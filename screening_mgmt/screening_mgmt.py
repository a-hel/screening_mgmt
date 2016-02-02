#!/usr/bin/python
"""
.. module:: screening_mgmt
    :platform: OSX, Windows
    :synopsis: SCREENING_MGMT: A module to automate data handling from screening experi-
ments. It is a GUI-based interface between raw experimental data and a data
base, where data is stored according to pre-defined routines. It also pro-
vides access to that data and displays it as plot or table.

Version: 0.1.1
Author: Andreas Helfenstein, andreas.helfenstein@helsinki.fi
Last revised: 19-09-2014
"""


import os
import re
import sys
import xlrd
import pandas
import time
import pickle
import ttk
import tkMessageBox
import tkSimpleDialog
import cmd
import collections
import shutil

import sqlalchemy as sa
import tkFileDialog as tkfd
import Tkinter as tk

from dateutil import parser
from ScrolledText import ScrolledText
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import mapper
from sqlalchemy import (Column, ForeignKey, String, Table, Boolean, Unicode,
    Float, Integer, DateTime, PickleType, or_, Interval)


__version__ = "1.0.0"
__license__ = ""
#__revision__ = ""
__docformat__ = "reStructuredText"

Base = declarative_base()



class DbError(Exception):
    """An error with the database communication"""

    def __init__(self,val):
        self.val = val

    def __str__(self):
        return repr(self.val)


def _construct(**kwargs):
    """Set attributes from kwargs.

    This method is used for in-line class creation.
    """

    for key in kwargs:
        setattr(self, key, kwargs[key])


class DbConnection(object):
    """
    Interface to the database connection.

    Set up connection to a supported SQL database via SQLAlchemy and
    collect the pointers to the ORM.

    .. class:: DbConnection()

        - **Parameters**:

            :param dialect: The database protocol. At the moment, *SQLAlchemy*
                supports the following protocols: *drizzle*, *firebird*, *mssql*,
                *mysql*, *oracle*, *postgresql*, *sqlite*, and *sybase*.

            :type dialect: String

            :param host: The host (e.g. *localhost* or `127.0.0.1`)
            :type host: String
            :param user: Username
            :type user: String
            :param pw: Password
            :type pw: String
            :param db: Database name
            :type db: String
            :param driver: Driver (default: "")
            :param key_val: Additional key values (default: "")
            :return: None
            :rtype: None

        - **Example**::

            :Example: balah

        - **See also**::

            .. seealso:: blah



    """

    def __init__(self, dialect, host, user, pw, db, driver=None, key_val=None):



        supported_db = {
            "Drizzle": "drizzle",
            "Firebird": "firebird",
            "Microsoft SQL Server": "mssql",
            "MySQL": "mysql",
            "Oracle": "oracle",
            "PostgreSQL": "postgresql",
            "SQLite": "sqlite",
            "Sybase": "sybase"
            }
        if dialect.lower() in supported_db.values():
            self.dialect = dialect
        else:
            raise DbError(
                "Dialect '{0}' is not supported, try '{1}'."
                .format(dialect, "', '".join(supported_db.values())))
            return
        self.host = host
        self.user = user
        self.pw = pw
        self.database = db
        if driver:
            self.driver = "+" + driver
        else:
            self.driver = ""
        self.key_val = key_val
        self.status = False

    def _initialize(self):
        """Create the standard tables Usr, Cpd, Rtn, Res."""

        if not self.status:
            try:
                self.connect()
            except DbError, e:
                print e
        if self.status:
            for tb in [Usr, Cpd, Rtn, Res]:
                tb.__table__
            self.metadata = Base.metadata
            self.metadata.create_all(self.engine)
        else:
            raise DbError("Could not establish connection to the database.")

    def _close_connection(self):
        """Close the connection."""

        self.engine.close()
        self.status = False

    def connect(self):
        """Connect to database, create engine and metadata.

        Returns two values: A boolean for successful/unsuccessful connection,
        and a string with a confirmation or error message.
        """

        url_params = [
            self.dialect,
            self.driver,
            self.user,
            self.pw,
            self.host,
            self.key_val,
            self.database]
        url = "{0}{1}://{2}:{3}@{4}/{5}{6}".format(*url_params)
        try:
            # Set echo to True to see SQL
            self.engine = sa.create_engine(url, echo=False)
        except sa.exc.ArgumentError, e:
            raise DbError("> The URL\n\n{0}\n\n is not valid.\n\n> {1}"
                .format(url, e))
        try:
            self.conn = self.engine.connect()
        except sa.exc.DBAPIError, e:  # Wrong password, user or server
            raise DbError(
                "> Check password, user name or server.\n\n> {0}".format(e))
        except sa.exc.ProgrammingError, e:  # Wrong database
            raise DbError("> Check database name.\n\n> {0}".format(e))
        self.metadata = sa.MetaData(bind=self.engine)
        Session = sa.orm.sessionmaker(bind=self.engine)
        self.session = Session()
        self.status = True
        return True, "Connection successfully established"

    def new_entry(self, target, data):
        """Insert a new entry into the target table.

        Arguments:
        target -- The name of the target database
        data -- A dict where the keys must correspond to the columns of the
                target table.
        """

        self.metadata.reflect(self.engine)
        entry = target(self, **data)
        self.session.add(entry)
        self.session.commit()  # To do: Catch exceptions

    def batch_load(self, target, delim=",", raw_file=None, update=False):
        """Load compound and user information from file.

        target -- The target database (e.g. Cpd, Rtn, Usr)
        delim -- Delimiter used in txt and csv files, default is comma (",").
                 This value is ignored when treating Excel files.
        source_file -- The file to be loaded. If omitted, it can be chosen
                       via a dialog.
        """

        if isinstance(target, basestring):
            target = eval(target)
        if target == Cpd:
            id_field = "name"
            table = self.metadata.tables['compounds']
        elif target == Usr:
            id_field = "usr_name"
            table = self.metadata.tables['users']
        self.metadata.reflect(self.engine)
        if not raw_file:
            raw_file = tkfd.askopenfilename(filetypes=[
                ('All files', '.*'),
                ('Text files', '.txt'),
                ('Comma-separated values','.csv'),
                ('Excel files', '.xls'),
                ('Excel XML files', '.xlsx')],
                title="Choose a file:")
        if raw_file:
            ext = raw_file.rsplit(".", 1)[-1]
            if ext in ["txt", "csv"]:
                with open(raw_file, mode="r") as input_file:
                    key = input_file.readline().split(delim)
                    for line in input_file:
                        dic = dict(zip(key, line.split(delim)))
                        entry = target(self, **dic)
                        self.session.add(entry)
                        try:
                            self.session.flush()
                        except (sa.exc.IntegrityError,
                                sa.exc.InvalidRequestError):
                            if update:
                                stmt = (
                                    table.update().
                                    where(table.c[id_field] == dic[id_field]).
                                    values(**dic))

                                self.engine.execute(stmt)
                                print "Record '{0}' updated."\
                                    .format(dic[id_field])
                            else:
                                print "Record '{0}' already exists."\
                                    .format(dic[id_field])
            elif ext in ['xls', 'xlsx']:
                workbook = xlrd.open_workbook(raw_file)
                worksheet = workbook.sheet_by_index(0)
                num_rows = worksheet.nrows - 1
                curr_row = 0
                key = worksheet.row_values(0, start_colx=0, end_colx=None)
                while curr_row < num_rows:
                    curr_row += 1
                    rowValues = worksheet.row_values(curr_row, start_colx=0,
                        end_colx=None)
                    dic = dict(zip(key, rowValues))
                    entry = target(self, **dic)
                    self.session.add(entry)
                    try:
                        self.session.flush()
                    except (sa.exc.IntegrityError,
                            sa.exc.InvalidRequestError):
                        if update:
                            stmt = (
                                table.update().
                                where(table.c[id_field] == dic[id_field]).
                                values(**dic))

                            self.engine.execute(stmt)
                            print "Record '{0}' updated."\
                                .format(dic[id_field])
                        else:
                            print "Record '{0}' already exists."\
                                .format(dic[id_field])

            else:
                tkMessageBox.showerror("Invalid file format",
                    "Could not open file of type '{0}'.\n".format(ext) +
                    "The following files are accepted: " +
                    "xls, xlsx, txt, csv.")
                return
            self.session.commit()

    def write_results(self, routine, user_dir, preview=False, *args, **kwargs):
        """Write a new dataset to the main table.

        The function loads the user scripts from the user's working directory.

        Arguments:

        routine -- The name of the routine
        args, kwargs -- Will be passed to the user script
        """

        declined_rtn = []
        sys.path.append(user_dir)
        try:
            exec("import {0} as rtn".format(routine)) in locals()
        except ImportError:
            if routine:
                errortext = ("""Module '{0}' not found in '{1}'\n.
                    \nDo you want to look for it yourself?"""
                    .format(routine, user_dir))
            else:
                errortext = ("""Please select the routine script.""")
            if tkMessageBox.askyesno("Module not found", errortext):
                loc = tkfd.askopenfilename(title="Select the script")
                try:
                    path, file_ = loc.rsplit(os.sep, 1)
                except ValueError:
                    path, file_ = loc.rsplit("/", 1)
                file_, _ = file_.rsplit(".",1)
                sys.path.append(path)
                try:
                    exec("import {0} as rtn".format(file_)) in locals()
                except ImportError:
                    tkMessageBox.showerror("Import error",
                        "The script '{0}' is not valid.".format(file_))
            else:
                return False
        if not hasattr(rtn, 'get_data'):
            tkMessageBox.showerror("Function not found",
                "The script '{0}' has no function 'get_data()'\n".format(file_) +
                "Please modify your script accordingly.")
            return False
        else:
            sets = (rtn.get_data(*args, **kwargs))
            struct = False
            if sets:
                if isinstance(sets, list):
                    if isinstance(sets[0], list):
                        if isinstance(sets[0][0], pandas.DataFrame)\
                        and isinstance(sets[0][1], dict):
                            struct = True
            if not struct:
                tkMessageBox.showerror("Structural error",
                        "Wrong format returned from 'get_data()'")
                return False
            if preview:
                root = tk.Tk()
                d = PreviewDialog(root, sets[0][0].head())
                root.wait_window(d.top)
                if not d.result:
                    root.destroy()
                    return False
                else:
                    root.destroy()

            for dataset in sets:
                meta_values = dataset[1]
                df = dataset[0]
                for record in df.to_dict(outtype="records"):
                    meta_values['sample'] = record['Sample']
                    current_record = Res(self, meta_values)
                    self.session.add(current_record)
                    self.metadata.reflect(self.engine)
                    self.metadata.bind = self.engine
                    try:
                        self.session.commit()
                        record['link'] = current_record.res_id
                        self.metadata.tables[meta_values['routine']]\
                            .insert(values=record).execute()

                    except KeyError, e:
                        e_str = str(e)
                        e_str = e_str.replace("'", "")
                        e_str = e_str.replace('"', '')
                        if e_str not in declined_rtn:
                            dialog = tkMessageBox.askyesno("Unknown routine",
                                "Would you like to automatically add the " +
                                "routine '{0}'?".format(e_str))
                            if dialog:
                                d_fields = {}
                                for keys in df.columns:
                                    if df[keys].dtypes == "bool":
                                        d_type = Boolean
                                    elif df[keys].dtypes in ["int16",
                                        "uint32"]:
                                        d_type = Integer
                                    elif df[keys].dtypes in ["float32",
                                        "float64"]:
                                        d_type = Float(precision=25)
                                    elif df[keys].dtypes == "cfloat":
                                        d_type = Unicode(50)
                                    elif df[keys].dtypes == "datetime64":
                                        d_type = DateTime
                                    elif df[keys].dtypes == "timedelta64":
                                        d_type = Interval
                                    #if isinstance(dataset[0], (int, long, float)):
                                    #    d_type = Float(precision=20)
                                    else:
                                        d_type = Unicode(200)

                                    d_fields[keys] = d_type

                                values = {"alias": e_str,
                                    "full_name": e_str,
                                    "data_dimension": 1,
                                    "author": meta_values["user"],
                                    "data_fields": d_fields,
                                    "script_path": (path, file_)}

                                self.new_entry(Rtn, values)

                                self.metadata.reflect(self.engine)
                                self.session.commit()
                                record['link'] = current_record.res_id
                                self.metadata.tables[meta_values['routine']]\
                                    .insert(values=record).execute()


                            else:
                                declined_rtn.append(e_str)

                    except:
                        # Necessary to keep the program going despite one bad set
                        e = sys.exc_info()
                        print ("Could not write \n{0}\nto Database. Error {1}"
                                .format(record, e))
                        continue
                self.session.commit()
                self.metadata.create_all(bind=self.engine, checkfirst=True)
                return True


    def load_results(self, filter_str,
            sl=True, sp=False, dl=False, dp=False):
        """Retrieve data from the database.

        Return the filtered data as a pandas data frame. Has to be called for
        every routine, since data sets from different routines might be in-
        compatible.
        Arguments:
        filter_str -- The filter string (SQLAlchemy syntax)
        sl -- Boolean whether to save the result as a list
        sp -- Boolean whether to save the result as a plot
        dl -- Boolean whether to display the result as a list
        dp -- Boolean whether to display the result as a plot
        """

        data_pool = {}
        df_pool = {}
        dir_pool = {}
        filter_object = eval(filter_str)
        try:
            if isinstance(filter_object, tuple):
                a = self.session.query(Res.res_id, Rtn.alias).join(Cpd, Usr)\
                    .filter(*filter_object).all()
            else:
                a = self.session.query(Res.res_id, Rtn.alias).join(Cpd, Usr)\
                    .filter(filter_object).all()
        except SyntaxError:
            raise DbError("Could not create filter\n{0}\n".format(filter_str) +
                "Please try again.")
            return
        #except sa.exc.ArgumentError:
        #    return
        if a:
            for result in a:
                routine = result[1]
                tbl = Table(routine, self.metadata, autoload=True,
                    autoload_with=self.engine)
                c = tbl.select().where(tbl.c.link == result[0])
                d = self.conn.execute(c).fetchone()
                if d is not None:
                    data_pool.setdefault(routine, []).append(d)
            for keys in data_pool:
                cols = [str(col).replace("{0}.".format(keys), "") for col in
                    self.metadata.tables[keys].columns]
                result_df = pandas.DataFrame(data=data_pool[keys], columns=cols)
                df_pool.setdefault(keys, result_df)
            dir_col = self.session.query(Rtn.alias, Usr.working_directory)\
                .filter(Rtn.alias.in_(set(zip(*a)[1])) ).all()
            dir_pool = dict(elem for elem in dir_col)
            return df_pool, dir_pool
        else:
            raise DbError("This search does not match any records.")

    def get_summary(self, routine, user_dir, df, plot=0, list_=1,
            *args, **kwargs):
        """Create a list for on-screen display or writing to file or
        a plot for on-screen display or writing to file.

        Calls the user-defined script associated with the routine.
        Arguments:
        routine -- The routine to be used
        df -- The database, preferably retrieved via load_results().
        plot -- boolean, whether plot is to be returned
        list_ -- boolean, whether list is to be returned
        """

        sys.path.append(user_dir)
        summary = {}
        try:
            exec("import {0} as rtn".format(routine)) in locals()
        except ImportError:
            errortext = ("""Module '{0}' not found in '{1}'.\n
                \nDo you want to look for it yourself?"""
                .format(routine, user_dir))
            if tkMessageBox.askyesno("Module not found", errortext):
                loc = tkfd.askopenfilename(title="Select the script")
                try:
                    path, file_ = loc.rsplit(os.sep, 1)
                except ValueError:
                    path, file_ = loc.rsplit("/", 1)
                sys.path.append(path)
                #try:
                exec("import {0} as rtn".format(file_.rsplit(".",
                        1)[0])) in locals()
                #except:
                #    raise DbError("Impossible to open script")
            else:
                return
        except SyntaxError:
            errortext = ("""Module '{0}' is defective.\n
                \nDo you want to use another one?"""
                .format(routine, user_dir))
            if tkMessageBox.askyesno("Choose module", errortext):
                loc = tkfd.askopenfilename(title="Select the script")
                try:
                    path, file_ = loc.rsplit(os.sep, 1)
                except ValueError:
                    path, file_ = loc.rsplit("/", 1)
                sys.path.append(path)
                try:
                    exec("import {0} as rtn".format(file_.rsplit(".",
                        1)[0])) in locals()
                except:
                    raise DbError("Impossible to open script")
            else:
                return
        if list_:
            if hasattr(rtn, 'summarize_list'):
                summary["list"] = (rtn.summarize_list(df, *args, **kwargs))
            else:
                summary["list"] = df.to_string(justify='left')
        if plot:
            if hasattr(rtn, 'summarize_plot'):
                summary["plot"] = (rtn.summarize_plot(df, *args, **kwargs))
            else:
                summary["plot"] = None
        return summary

    def update(self, table, id_field, id_value, val):
        """Update a field in the database.

        Arguments:
        table -- The table that should be updated
        id_code -- The primary key for the row to be updated
        kwargs -- The keys must match the column names, the values are the
                  updated values.
        """

        stmt = (
            table.update().
            where(table.c[id_field] == id_value).
            values(**val))
        self.engine.execute(stmt)


class Cpd(Base):
    """Class for the compound table"""

    __tablename__ = "compounds"
    cpd_id = Column(Integer, primary_key=True)
    name = Column(String(200), unique=True, nullable=False)
    group = Column(String(200))
    smiles = Column(String(50))
    cas = Column(String(20))
    formula = Column(String(50))
    address = Column(String(50))
    batch = Column(String(20))

    def __init__(self, conn, **kwargs):
        """Constructor"""

        for key in kwargs:
            setattr(self, key, kwargs[key])

class Usr(Base):
    """Class for the user table."""

    __tablename__ = "users"
    usr_id = Column(Integer, primary_key=True)
    usr_name = Column(String(20), unique=True, nullable=False)
    first_name = Column(String(50))
    middle_name = Column(String(50))
    last_name = Column(String(50))
    e_mail = Column(String(100))
    affiliation = Column(String(100))
    degree = Column(String(50))
    phone = Column(String(20))
    working_directory = Column(String(200))

    def __init__(self, conn, **kwargs):
        """Construct user table and user directory.

        If no user directory is defined in kwargs, a folder in the home
        directory is created.
        """

        for key in kwargs:
            setattr(self, key, kwargs[key])
        if not self.working_directory:
            import os
            usr_path = os.path.expanduser("~/{0}".format(self.usr_name))
            try:
                os.makedirs(usr_path)
            except OSError, e:
                print "Could not create user directory: {0}".format(e)
            self.working_directory = usr_path


class Rtn(Base):
    """Class for the routine table"""

    __tablename__ = "routines"
    rtn_id = Column(Integer, primary_key=True)
    alias = Column(String(20), unique=True, nullable=False)
    author = Column(String(20), ForeignKey('users.usr_name'))
    full_name = Column(String(200))
    description = Column(String(200))
    sop = Column(String(100))
    data_location = Column(String(20))
    data_dimension = Column(Integer, nullable=False)
    data_fields = Column(PickleType, nullable=False)

    def __init__(self, conn, **kwargs):
        """Constructs the table.

        If the specified user is not known, a new user record is created.
        In the user directory, a template for the input/output functions is
        created.
        Also creates a new table with columns according to data_fields.
        """

        for key in kwargs:
            if key is not "script_path":
                setattr(self, key, kwargs[key])
            else:
                script_path = kwargs[key]
        if self.author:
            if not conn.session.query(Usr.usr_name)\
                    .filter(Usr.usr_name == self.author).first():
                conn.new_entry(Usr, {"usr_name": self.author})
        cols = [
            Column('id', Integer, primary_key=True),
            Column('link', Integer, ForeignKey('results.res_id'))]
        for keys in self.data_fields:
            cols.append(Column(keys, self.data_fields[keys]))
        cls = Table(self.alias, conn.metadata,
                *cols)
        dyn_class = type(self.alias, (object,), {'__tablename__': self.alias,
                '__init__': _construct})
        mapper(dyn_class, cls)
        conn.metadata.create_all(bind=conn.engine)
        self.usr_dir = (
            conn.session.query(Usr.working_directory)
            .filter(Usr.usr_name==self.author).one())
        if not script_path:
            _get_rtn_files(self)
        else:
            file_path = os.sep.join(script_path) + ".py"
            usr_dir = self.usr_dir[0]
            shutil.copy(file_path, usr_dir)
            new_path = os.sep.join([usr_dir, script_path[1]]) + ".py"
            new_name = os.sep.join([usr_dir, self.alias]) + ".py"
            try:
                os.rename(new_path, new_name)
            except WindowsError:
                print "File already exists"




class Res(Base):
    """Class for the result metadata table."""

    __tablename__ = "results"
    res_id = Column(Integer, primary_key=True)
    sample = Column(Integer, ForeignKey('compounds.cpd_id'))
    user = Column(Integer, ForeignKey('users.usr_id'))
    date = Column(DateTime)
    routine = Column(Integer, ForeignKey('routines.rtn_id'))
    active = Column(Boolean)
    raw_data_id = Column(Integer, unique=False)

    def __init__(self, conn, meta_data):
        """Constructor"""

        date = meta_data['date']
        if type(date) == int or float:
            xld = xlrd.xldate_as_tuple(date, 1)
            date = "{2}.{1}.{0}".format(*xld)
            self.date = parser.parse(date, dayfirst=True, fuzzy=True)
        else:
            try:
                self.date = parser.parse(date)
            except ValueError:
                self.date = 0
        self.active = meta_data['active']
        if (
                conn.session.query(Cpd.cpd_id)
                .filter(Cpd.name == meta_data['sample'])
                .count() == 0):
            conn.new_entry(Cpd, {"name": meta_data['sample']})
        self.sample = (
                conn.session.query(Cpd.cpd_id)
                .filter(Cpd.name == meta_data['sample']).scalar())
        if (
                conn.session.query(Usr.usr_id)
                .filter(Usr.usr_name == meta_data['user'])
                .count() == 0):
            conn.new_entry(Usr, {"usr_name": meta_data['user']})
        self.user = (
                conn.session.query(Usr.usr_id)
                .filter(Usr.usr_name == meta_data['user']).scalar())
        if (
                conn.session.query(Rtn.rtn_id)
                .filter(Rtn.alias == meta_data['routine'])
                .count() == 0):
            print "Routine does not exist"
            return
        self.routine = (
                conn.session.query(Rtn.rtn_id)
                .filter(Rtn.alias==meta_data['routine'])
                .scalar())


class CmdLine(cmd.Cmd):
    """Start simple command processor for debugging/low level functions."""

    def __init__(self):
        cmd.Cmd.__init__(self)
        conn = []
        try:
            rec_conn = pickle.load(open( "connections.p", "rb" ))
        except IOError:
            rec_conn = []
        enum_conn = enumerate(rec_conn)
        print "Chose a connection or type 'n' for a new connection:"
        for elem in enum_conn:
            print "{0}: {1}".format(elem[0], " ".join(elem[1]))
        choice = raw_input()
        if choice.lower() == "n":
            for elem in ["Protocol: ",
                "Host: ",
                "User: ",
                "Password: ",
                "Database: ",
                "Driver: ",
                "Key values: "]:
                conn.append(raw_input(elem))

        else:
            choice = int(choice)
            conn += rec_conn[choice][0:3]
            conn.append(raw_input("Password:"))
            conn += rec_conn[choice][4:]

        self.connection = DbConnection(*conn)
        self.connection.connect()
        self.prompt = '>>> '


    def do_usr(self, line):
        """Add the user [line]."""

        user = {"usr_name": line,}
        try:
            self.connection.new_entry(Usr, user)
            print("User {0} added.".format(line))
        except sa.exc.InvalidRequestError, e:
            print ("Could not add the user: \n\n{0}".format(e))
        except sa.exc.IntegrityError:
            print "A user with the name '{0}' already exists.".format(line)

    def do_init(self, line):
        """Build the database tables."""

        try:
            self.connection._initialize()
            print("Database initialized.")
        except:
            e = sys.exc_info()
            print ("Could not initialize the Database: \n\n{0}".format(e))

    def do_reset(self, line):
        """Drop all tables irreversibly and rebuild the basic
        tables of the database.
        """

        confirmation = raw_input("This will delete all tables. "+
            "Are you sure? [Y/N]")
        if confirmation.lower() in ['y','yes']:
            self.connection.metadata.reflect(self.connection.engine)
            for table in reversed(self.connection.metadata.sorted_tables):
                try:
                    table.drop()
                except sa.exc.UnboundExecutionError, e:
                    print e
                    print "Could not reset database. Try again"
            self.connection._initialize()
            print("Database reset.")

    def do_exe(self, line):
        """Execute line as SQL statement.
        """

        print "IN: >> {0}".format(line)
        try:
            result = self.connection.conn.execute(line)
        except sa.exc.ProgrammingError, e:
            result = str(e)

        print "OUT: >> {0}".format(result)

    def do_summary(self, line):
        """Show a list of the existing tables and the columns
        of the table specified in line.
        """

        self.connection.metadata.reflect(self.connection.engine)
        print "\nTables in database:\n"
        print ", ".join(self.connection.metadata.tables.keys())
        if line:
            print "\nColumns in Table {0}:\n".format(line)
            try:
                print ", ".join(self.connection.metadata.tables[line].columns)
            except:
                print "Table '{0}' not found.".format(line)

    def do_load(self, line):
        """Load the first ten sets of the routine specified in line"""

        sys.path.append("/routines")
        cmd = "import routines.{0} as rtn".format(line)
        exec(cmd)
        self.connection.write_results(rtn.get_data())

    def do_db(self, line):
        """Applies the command to the connection, stub"""

        try:
            eval("connection.{0}".format(line))
        except:
            e = sys.exc_info()
            print ("Invalid command: \n\n{0}".format(e))

    def do_enter(self, line):
        """Enters new data sets"""

        args = line.split(" ")
        exec("import {0} as rtn".format(args.pop(0))) in locals()
        reload(rtn)
        try:
            results = rtn.load_data()
        except:
            e = sys.exc_info()
            print ("Error: \n\n{0}".format(e))
        self.connection.write_results(results)

    def do_sql(self, line):
        """Executes SQL statement"""
        try:
            self.connection.engine.execute(line)
        except sa.exc.ProgrammingError, e:
            print "Synatx error. \n {0}".format(e)

    def do_ud(self, line):
        """reloads modules"""
        for mod in [sm,]:
            reload(mod)

    def do_close(self, line):
        """Closes the connection"""
        try:
            self.connection.close()
        except AttributeError:
            print "No active connection"

    def do_gui(self, line):
        """Start the GUI."""


        root = tk.Tk()
        root.title('Database connection')
        connection_dlg = MainMenu(root, self.connection)
        root.wait_window(connection_dlg.parent)


    def do_EOF(self, line):
        """Quits the console."""
        return True

    def do_exit(self, line):
        """Quits the console."""
        return True

    def do_quit(self, line):
        """Quits the console."""
        return True

class DB_connection():

    def __init__(self, parent):
        """Show the input mask to connect to the database.

        Refer to the documentation for a detailed description.
        """

        try:
            self.rec_conn = pickle.load(open( "connections.p", "rb" ))
        except IOError:
            self.rec_conn = [('mysql', '127.0.0.1', 'root', '', 'main', '', '')]
        self.parent = parent
        self.conn = False
        self.input_fields = []
        self.field_names = [
            "Protocol",
            "Host",
            "User",
            "Password",
            "Database"
            ]
        self.pw_field = self.field_names[3]
        self.db_list = {
            "Drizzle": "drizzle",
            "Firebird": "firebird",
            "Microsoft SQL Server": "mssql",
            "MySQL": "mysql",
            "Oracle": "oracle",
            "PostgreSQL": "postgresql",
            "SQLite": "sqlite",
            "Sybase": "sybase"
            }
        f = tk.Frame(self.parent, padx=1, pady=1, bd=5)
        f.pack()
        for field in range(0, len(self.field_names)):
            tk.Label(f, text=self.field_names[field],
                font=("Helvetica", 12),
                justify = "left").grid(row=2, column=1+field, sticky="w")
            cur_field = tk.Entry(f,
                bd=2)
            if self.field_names[field] == self.pw_field:
                cur_field.config(show="*")
            cur_field.grid(row=3, column=1+field, sticky="w")
            self.input_fields.append(cur_field)

        self.l_driver = tk.Label(f, text="Driver",
                font=("Helvetica", 12),
                justify="left")
        self.e_driver = tk.Entry(f,
                bd=2)
        self.l_keyval = tk.Label(f, text="Key values",
                font=("Helvetica", 12),
                justify="left")
        self.e_keyval = tk.Entry(f,
                bd=2)
        self.input_fields.append(self.e_driver)
        self.input_fields.append(self.e_keyval)
        self.L0 = tk.Label(f,
            text="Connect to SQL database",
            font=("Helvetica", 20),
            justify="left")
        self.L0.grid(row=0, column=0, columnspan=3, sticky="w")
        self.exit = tk.Button(f
            , text="Cancel", command=lambda: self.quit(), width=15)
        self.exit.grid(row=4, column=field, sticky="e")
        self.okbutton = tk.Button(f,
            text="Connect",command=lambda: self.connect(), width=15)
        self.okbutton.grid(row=4, column=1+field, sticky="w")
        self.menubar = tk.Menu(self.parent)
        filemenu = tk.Menu(self.menubar, tearoff=0)
        filemenu.add_command(label="About", command=self._get_about)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.quit)
        self.menubar.add_cascade(label="File", menu=filemenu)
        recentmenu = tk.Menu(self.menubar, tearoff=0)
        for rc in self.rec_conn:
            recentmenu.add_command(label=" ".join(rc),
            command=self._get_ref(rc))
        self.menubar.add_cascade(label="Recent", menu=recentmenu)
        optmenu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="Options", menu=optmenu)
        dbmenu = tk.Menu(optmenu, tearoff=0)
        for key in self.db_list:
            dbmenu.add_command(label=key, command=self._rep_field(key))
        optmenu.add_cascade(label="Databases", menu=dbmenu)
        optmenu.add_command(label="Show/hide password", command=self._toggle_pw)
        optmenu.add_command(label="Show more connection options",
            command=self._conn_options)
        optmenu.add_command(label="Help", command=self._show_help)
        self.parent.config(menu=self.menubar)
        self.input_fields[0].focus_set()

    def _rep_field(self, x):
        """Return autofill function for the dialect box"""

        def on_click():
            self.input_fields[0].delete(0, tk.END)
            self.input_fields[0].insert(0, self.db_list[x])
        return lambda: on_click()

    def _get_ref(self, x):
        """Return autofill function for the dialect box"""

        def on_click():
            for i in range(0, len(self.input_fields)):
                self.input_fields[i].delete(0, tk.END)
                self.input_fields[i].insert(0, x[i])
                self.input_fields[3].focus_set()
        return lambda: on_click()



    def _toggle_pw(self):
        """Show or hide password"""

        pos = self.field_names.index(self.pw_field)
        if not self.input_fields[pos].cget("show"):
            self.input_fields[pos].config(show="*")
        else:
            self.input_fields[pos].config(show="")

    def _conn_options(self):
        """Show the additional text boxes"""

        self.l_driver.grid(row=4, column=1, sticky="w")
        self.l_keyval.grid(row=4, column=2, sticky="w")
        self.e_driver.grid(row=5, column=1, sticky="w")
        self.e_keyval.grid(row=5, column=2, sticky="w")
        self.e_driver.focus_set()

    def _get_about(self):
        """Show info"""

        tkMessageBox.showinfo("About", "Screening Managemant Software\n\n" +
            "Andreas Helfenstein\n" +
            "University of Helsinki\n\n" +
            "andreas.helfenstein@helsinki.fi")

    def _protect(self, param_list, blank_text=""):
        """Remove passwords from list"""

        pos = self.field_names.index(self.pw_field)
        param_list[pos] = blank_text
        return param_list

    def _load_rc(self, rc):
        """Paste recent connection value into fields"""

        for i in range(0, len(self.input_fields)):
            self.input_fields[i].delete(0, tk.END)
            self.input_fields[i].insert(0, rc[i])
            self.input_fields[3].focus_set()

    def _show_help(self):
        """Show the documentation"""

        def we_are_frozen():
            # All of the modules are built-in to the interpreter, e.g., by py2exe
            return hasattr(sys, "frozen")

        def module_path():
            encoding = sys.getfilesystemencoding()
            if we_are_frozen():
                return os.path.dirname(unicode(sys.executable, encoding))
            return os.path.dirname(unicode(__file__, encoding))

        filename = module_path() + os.sep + "doc.pdf"

        if sys.platform.startswith('darwin'):
            os.system("open " + filename)
        elif sys.platform.startswith('linux'):
            import subprocess
            subprocess.call(('xdg-open', filename))
        elif sys.platform.startswith('win32'):
            os.startfile(filename)


    def connect(self):
        """Connect to database and open Main Menu"""

        conn_params = []
        for field in self.input_fields:
            conn_params.append(field.get())
        try:
            self.connection = DbConnection(*conn_params)
            self.conn = self.connection.connect()
        except DbError, e: #wrong pw, user, server
            tkMessageBox.showerror("Connection problem",
                "> Could not connect to the database.\n\n" +
                "Original message:\n {0}".format(e))
            return

        conn_params = self._protect(conn_params)
        if conn_params not in self.rec_conn:
            self.rec_conn.append(conn_params)
        if len(self.rec_conn) > 5:
            self.rec_conn = self.rec_conn[-5:]
        pickle.dump(self.rec_conn, open( "connections.p", "wb" ))
        self.newWindow = tk.Toplevel(self.parent)
        self.app = MainMenu(self.newWindow, self.connection)

    def quit(self):
        self.conn = True
        self.parent.destroy()


class MainMenu():

    def __init__(self, parent, conn):
        """The Main GUI"""

        self.parent = parent
        self.conn = conn
        self.filter_elements=[]
        self.var_collection={}


        filter_fields = (
            ("Choose criteria", None),
            ("Compound name", "Cpd.name"),
            ("Compound group", "Cpd.group"),
            ("SMILES", "Cpd.smiles"),
            ("CAS number", "Cpd.cas"),
            ("Formula", "Cpd.formula"),
            ("Batch number", "Cpd.batch"),
            ("User name", "Usr.usr_name"),
            ("User: First name", "Usr.first_name"),
            ("User: Last name", "Usr.last_name"),
            ("User: Affiliation", "Usr.affiliation"),
            ("Routine", "Rtn.alias"),
            ("Author", "Rtn.author"))
        self.filter_fields = collections.OrderedDict(filter_fields)

        self.comp = ("==", "!=", "<=", ">=", "IN", "NOT IN", "LIKE")
        conn.metadata.reflect(conn.engine)

        nb = ttk.Notebook(self.parent, height=500, padding=5, width=550)
        self.q_frame = tk.Frame(nb, padx=5, pady=5)
        self.m_frame = tk.Frame(nb, padx=5, pady=5)
        self.l_frame = tk.Frame(nb, padx=5, pady=5)
        self.o_frame = tk.Frame(nb, padx=5, pady=5)

        nb.add(self.q_frame, text="Query")
        nb.add(self.m_frame, text="Manage")
        nb.add(self.l_frame, text="Add")
        #nb.add(self.o_frame, text="Options")

        q_descript = ("Choose the filter criteria for your search and the " +
            "output mode.\nClick 'Preview' to see and modify your query.")
        m_descript = ("Manage the database tables or load compounds or users \n" +
            "directly from a file. If you select 'Update existing', \n" +
            "existing records will be overwritten.")
        l_descript = ("Add new results to your database. If you choose " +
            "'Custom',\nyou can select the import script manually.")

        nb.pack()

        self.c1 = tk.IntVar()
        self.c2 = tk.IntVar()
        self.c3 = tk.IntVar()
        self.c4 = tk.IntVar()
        self.v = v = tk.StringVar()
        self.d = d = tk.StringVar()
        self.u = u = tk.IntVar()

        tk.Label(self.q_frame, text="Get data",
            font=("Helvetica", 16),
            pady=3,
            justify="left").grid(row=0, column=0, columnspan=3, sticky="w")
        tk.Label(self.q_frame, text=q_descript, pady=3,
            justify="left").grid(row=1, column=0, columnspan=3, sticky="w")
        tk.Button(self.q_frame, text="Ok", command=lambda: self._get_results(self._options()),
            width=12).grid(row=2, column=4, sticky="we")
        tk.Button(self.q_frame, text="Preview", command=lambda: self._get_preview(self._options()),
            width=12).grid(row=3, column=4, sticky="we")
        tk.Button(self.q_frame, text="Reset", command=lambda: self._form_reset(),
            width=12).grid(row=4, column=4, sticky="we")
        tk.Button(self.q_frame, text="Exit",
            command=lambda: self.quit(),
            width = 12).grid(row=5, column=4, sticky="we")
        tk.Checkbutton(self.q_frame, variable=self.c1, text="Show graphs",
            ).grid(row=2, column=0)
        cb = tk.Checkbutton(self.q_frame, variable=self.c2,
            text="Show table")
        cb.grid(row=2, column=1)
        cb.select()
        tk.Checkbutton(self.q_frame, variable=self.c3,
            text="Save graphs").grid(row=2, column=2)
        tk.Checkbutton(self.q_frame, variable=self.c4,
            text="Save table").grid(row=2, column=3)

        self.obj_collection={}

        self._new_line(0, 2)

        # self.m_frame: Modification frame
        tk.Label(self.m_frame, text="Manage data",
            font=("Helvetica", 16),
            pady=3,
            justify="left").grid(row=0, column=1, columnspan=3, sticky="w")
        tk.Label(self.m_frame, text=m_descript, pady=3,
            justify="left").grid(row=1, column=1, columnspan=3, sticky="w")
        tk.Button(self.m_frame, text="Manage routines",
            command=lambda: self._mg_rtn(),
            width=20, height=4, justify="center").grid(row=2, column=1)
        tk.Button(self.m_frame, text="Manage users",
            command=lambda: self._mg_usr(),
            width=20, height=4, justify="center").grid(row=2, column=2)
        tk.Button(self.m_frame, text="Manage compounds",
            command=lambda: self._mg_cpd(),
            width=20, height=4, justify="center").grid(row=2, column=3)
        tk.Label(self.m_frame, text="Load from file:",
            font=("Helvetica", 14)).grid(row=3,
            column=1, sticky="w")
        tk.Label(self.m_frame, text="Database:").grid(row=4, column=1, sticky="w")
        tk.Radiobutton(self.m_frame, text="Compounds", variable=v,
            value="Cpd").grid(row=5, column=1, sticky="w")
        tk.Radiobutton(self.m_frame, text="Users", variable=v,
            value="Usr").grid(row=6, column=1, sticky="w")
        tk.Label(self.m_frame, text="Delimiter:").grid(row=4, column=2, sticky="w")
        tk.Radiobutton(self.m_frame, text="Comma", variable=d,
            value=",").grid(row=5, column=2, sticky="w")
        tk.Radiobutton(self.m_frame, text="Tab", variable=d,
            value="\t").grid(row=6, column=2, sticky="w")
        tk.Radiobutton(self.m_frame, text="Whitespace", variable=d,
            value=" ").grid(row=7, column=2, sticky="w")
        tk.Radiobutton(self.m_frame, text="Semicolon", variable=d,
            value=";").grid(row=8, column=2, sticky="w")
        tk.Checkbutton(self.m_frame, text="Update existing", variable=u,
           ).grid(row=5, column=3, sticky="w")
        tk.Button(self.m_frame, text="Load",
            command=lambda: self._b_load(),
            width=12, justify="center").grid(row=4, column=3, sticky="w")
        tk.Button(self.m_frame, text="Exit",
        command=lambda: self.quit(),
            width=12, justify="center").grid(row=8, column=3, sticky="w")
        v.set("Cpd")
        d.set(",")

        # self.l_frame: load frame
        a = tk.StringVar()
        self.p = p = tk.IntVar()
        routine_names = self.conn.session.query(
            Rtn.alias, Rtn.full_name,
            Rtn.description, Usr.working_directory).all()# perhaps join?
            #.filter(Rtn.author == Usr.usr_name).all()

        if not routine_names:
            routine_names = [["","No routines yet"],]
        self.routine_dict = {
            rtn[1]: rtn for rtn in routine_names}


        tk.Label(self.l_frame, text="Add data",
            pady=3,
            font=("Helvetica", 16),
            justify="left").grid(row=0, column=0, columnspan=3, sticky="w")
        tk.Label(self.l_frame, text=l_descript, pady=3,
            justify="left").grid(row=1, column=0, columnspan=3, sticky="w")

        selector = tk.OptionMenu(self.l_frame, a, "Custom...", *zip(*routine_names)[1],
            command=lambda val: self._update_rtn(val))

        tk.Label(self.l_frame, text="Routine:",
            justify="left").grid(row=2, column=0, sticky="w")
        selector.grid(row=2, column=1, sticky="we")

        tk.Label(self.l_frame, text="From:",
            justify="left").grid(row=3, column=0, sticky="w")
        self.fr = tk.Entry(self.l_frame)
        self.fr.grid(row=3, column=1)

        tk.Label(self.l_frame, text="To:",
            justify="left").grid(row=3, column=2, sticky="w")
        self.to = tk.Entry(self.l_frame)
        self.to.grid(row=3, column=3)

        tk.Label(self.l_frame, text="Newer than:",
            justify="left").grid(row=4, column=0, sticky="w")
        self.nt = tk.Entry(self.l_frame)
        self.nt.grid(row=4, column=1)

        tk.Label(self.l_frame, text="Keywords:").grid(row=4, column=2, sticky="w")
        self.kw = tk.Entry(self.l_frame)
        self.kw.grid(row=4, column=3)
        tk.Button(self.l_frame, text="Load...", width=12,
            command=lambda: self._load()).grid(row=5, column=3, sticky="we")
        tk.Checkbutton(self.l_frame, text="Preview", variable=p,
           ).grid(row=5, column=2, sticky="w")
        tk.Button(self.l_frame, text="Exit",
            command=lambda: self.quit(),
            width=12, justify="center").grid(row=6, column=3, sticky="we")
        self.menubar = tk.Menu(self.parent)
        filemenu = tk.Menu(self.menubar, tearoff=0)
        #filemenu.add_command(label="Drop tables", command=self.db.metadata.drop_all)
        #filemenu.add_command(label="Initialize tables", command=init_db)
        #filemenu.add_command(label="Backup", command=self.backup_db)
        filemenu.add_command(label="Help", command=self._show_help)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.quit)
        self.menubar.add_cascade(label="File", menu=filemenu)


        self.parent.config(menu=self.menubar)

        #nb.pack()



    def _options(self):
        """get kwargs"""
        return {}

    def _b_load(self):
        target = self.v.get()
        delim = self.d.get()
        ud = self.u.get()
        try:
            self.conn.batch_load(target, delim, update=ud)
        except KeyError, e:
            print "The file format is not correct.\n{0}".format(e)

    def _getln(self, line_number):

        def on_click():
            val = self.var_collection[line_number][0].get()
            if not val == "Choose criteria":
                unique_values = [re.sub(r'[^\x00-\x7f]',r'_',value[0]) for value in\
                    self.conn.session.query(eval(self.filter_fields[val]))\
                    .distinct() if value[0]]
                self.obj_collection[line_number].configure(values=unique_values)

        return lambda x: on_click()

    def _new_line(self, val, line_number):
        ax = [tk.StringVar(), tk.StringVar(), tk.StringVar(), tk.StringVar()]
        self.var_collection[line_number] = ax
        selector = tk.OptionMenu(self.q_frame, ax[0], *self.filter_fields.keys(),
            command=self._getln(line_number))
        ax[0].set("Choose criteria")
        comparator = tk.OptionMenu(self.q_frame, ax[1],
            *self.comp)
        ax[1].set("==")
        entry_line = ttk.Combobox(self.q_frame, textvariable=ax[2], width=15)
        self.obj_collection[line_number] = entry_line
        cupola = tk.OptionMenu(self.q_frame, ax[3], "AND", "OR",
            command=lambda val: self._new_line(val,line_number))
        selector.grid(column=0, row=line_number+1, sticky="we")
        comparator.grid(column=1, row=line_number+1, sticky="we")
        entry_line.grid(column=2, row=line_number+1, sticky="we")
        cupola.grid(column=3, row=line_number+1, sticky="we")
        line_number += 1
        self.filter_elements.append([selector, comparator, entry_line, cupola])

    def _form_reset(self):
        for l in self.filter_elements:
            for obj in l:
                obj.destroy()
        self.obj_collection={}
        self.var_collection={}
        self._new_line(0, 2)


    def _update_rtn(self, val):
        if val != "Custom...":
            self.current_rtn = self.routine_dict[val][0]
            self.user_dir = self.routine_dict[val][3]
        else:
            self.current_rtn = None
            self.user_dir = None

        #set description field

    def _load(self):
        kw = {}
        preview = self.p.get()
        if self.nt.get():
            kw["newer_than"] = self.nt.get()
        if self.fr.get():
            start = int(self.fr.get())
        else:
            start = 1
        if self.to.get():
            kw["load_range"] = range(start, int(self.to.get()))
        if self.conn.write_results(
            self.current_rtn,
            self.user_dir,
            preview = preview,
            **kw):

            tkMessageBox.showinfo("Import finished",
                    "Results loaded")

    def _show_help(self):
        """Show the documentation"""

        def we_are_frozen():
            # All of the modules are built-in to the interpreter, e.g., by py2exe
            return hasattr(sys, "frozen")

        def module_path():
            encoding = sys.getfilesystemencoding()
            if we_are_frozen():
                return os.path.dirname(unicode(sys.executable, encoding))
            return os.path.dirname(unicode(__file__, encoding))

        filename = module_path() + os.sep + "doc.pdf"

        if sys.platform.startswith('darwin'):
            os.system("open " + filename)
        elif sys.platform.startswith('linux'):
            import subprocess
            subprocess.call(('xdg-open', filename))
        elif sys.platform.startswith('win32'):
            os.startfile(filename)

    def _get_results(self, query_line=None, *args, **kwargs):

        text = ""
        if not query_line:
            query_line = self._build_query(**kwargs)
        try:
            results, user_dir = self.conn.load_results(query_line)
        except DbError, e:
            tkMessageBox.showerror("Database error", e)
            return

        if self.c1.get() or self.c3.get():
            pl_val = 1
        else:
            pl_val = 0
        if self.c2.get() or self.c4.get():
            li_val = 1
        else:
            li_val = 0

        for keys in results:
            summary = self.conn.get_summary(keys, user_dir[keys], results[keys],
                plot=pl_val, list_=li_val, **kwargs)

            if self.c1.get():
                # Show graphs
                summary['plot'].show()

            if self.c3.get():
                # save graphs
                filename = "{0}graphs_{1}_{2}.png".format(user_dir[keys],
                    keys, time.strftime("%d_%m_%Y"))
                summary['plot'].savefig(filename, bbox_inches='tight')

            if li_val:
                text += summary['list']
                text += "\n\n\n"

        if self.c2.get:
            self.newWindow = tk.Toplevel(self.parent)
            self.app = ListMenu(self.newWindow, text)

        if self.c4.get:
            filename = "{0}summary_{1}.png".format(user_dir[keys], keys,
                time.strftime("%d_%m_%Y"))
            f = open(filename, "w")
            f.write(text.encode('utf-8'))
            f.close()

    def _build_query(self, **kwargs):
        """Assemlbe the query string to be passed to the engine"""

        filter_str =[]
        comp_list = (self.var_collection[keys][3].get() for keys in self.var_collection)
        ors = [i for i, j in enumerate(comp_list) if j == "OR"]
        for i in range(len(self.var_collection)):
            if i in ors:
                if i-1 not in ors:
                    lead = "or_("
                else:
                    lead = ""
                if i in ors:
                    tail = ""
                else:
                    tail = ")"
            else:
                lead = ""
                if i-1 in ors:
                    tail = ")"
                else:
                    tail = ""
            if self.var_collection[i+2][1].get() == "IN":
                center = "{0}.in_(['{1}'])".format(
                   self.filter_fields[self.var_collection[i+2][0].get()],
                   "', '".join(self.var_collection[i+2][2].get().split(", ")))
            elif self.var_collection[i+2][1].get() == "NOT IN":
                center = "~{0}.in_(['{1}'])".format(
                  self.filter_fields[ self.var_collection[i+2][0].get()],
                   "', '".join(self.var_collection[i+2][2].get().split(", ")))
            elif self.var_collection[i+2][1].get() == "LIKE":
                center = "{0}.like('%{1}%')".format(
                   self.filter_fields[self.var_collection[i+2][0].get()],
                   self.var_collection[i+2][2].get())
            else:
                center = "{0} {1} '{2}'".format(
                   self.filter_fields[self.var_collection[i+2][0].get()],
                   self.var_collection[i+2][1].get(),
                   self.var_collection[i+2][2].get())

            filter_str.append("{0}{1}{2}".format(
                    lead, center, tail))

        return ", ".join(filter_str)


    def _get_preview(self, kwargs):
        query_line = self._build_query(**kwargs)
        new_query = tkSimpleDialog.askstring("Modify query",
            "Modify the query.\nUse SQLAlchemy syntax",
            initialvalue=query_line)
        print new_query
        if new_query:
            self._get_results(query_line=new_query)





    def backup_db(self):
        pass
    def _mg_rtn(self):
        self.newWindow = tk.Toplevel(self.parent)
        self.app = RtnMenu(self.newWindow, self.conn)

    def _mg_usr(self):
        self.newWindow = tk.Toplevel(self.parent)
        self.app = UsrMenu(self.newWindow, self.conn)
    def _mg_cpd(self):
        self.newWindow = tk.Toplevel(self.parent)
        self.app = CpdMenu(self.newWindow, self.conn)
    def show_results(self):
        pass

    def quit(self):
        self.parent.destroy()


class RtnMenu():

    def __init__(self, parent, conn):
        """The Main GUI"""

        global line_no

        self.parent = parent
        self.conn = conn
        self.elem_collection = {}
        all_rtn = [re.sub(r'[^\x00-\x7f]',r'_',value[0])\
            for value in\
            self.conn.session.query(Rtn.alias)\
            .distinct()]
        f = tk.Frame(self.parent, pady=5, padx=5)


        self.form = collections.OrderedDict((
            ("alias", [
                "Short name*:",
                tk.StringVar(),
                [ttk.Combobox(f, values=all_rtn),]]),
            ("full_name", [
                "Full name:",
                tk.StringVar(),
                [tk.Entry(f)],],),
            ("author", [
                "Author:",
                tk.StringVar(),
                [tk.Entry(f),]],),
            ("description", [
                "Description:",
                tk.StringVar(),
                [ScrolledText(f,
                font=('consolas', '12'), width=12, height=10),]],),
            ("sop", [
                "SOP:",
                tk.StringVar(),
                [tk.Entry(f),
                tk.Button(f, text="Browse...",
                command=lambda: self._browse_sop()),
                tk.Button(f, text="Open",
                command=lambda: self._open_sop())]])
        ))
        self.type_list=[
            "Unicode(20)",
            "Integer",
            "Float(precision=10)",
            "DateTime",
            "--------",
            "Boolean",
            "Date",
            "DateTime",
            "Enum()",
            "Float()",
            "Integer",
            "Interval()",
            "PickleType()",
            "String()",
            "Time()",
            "Unicode()"
            ]
        self.line_no = 1

        f.pack()
        self.f = f

        tk.Label(f, text="New routine",
                font=("Helvetica", 14),
                pady=3,
                justify = "left").grid(row=0,
                    column=0,
                    columnspan=2,
                    sticky="w")

        for keys in self.form:
            tk.Label(f, text=self.form[keys][0]).grid(row=self.line_no,
                    column=0, sticky="nw")
            for i in range(len(self.form[keys][2])):
                self.form[keys][2][i].grid(row=self.line_no,
                        column=1+i, sticky="we")
            self.line_no += 1


        def new_line():


            elems = [
                tk.Entry(f,),
                ttk.Combobox(f, values=self.type_list)]
            self.elem_collection[self.line_no] = elems
            for i in range(len(elems)):
                elems[i].grid(row=self.line_no, column=i+1, sticky="we")
            self.line_no += 1

        new_line()

        tk.Button(f, text="Close", command=lambda: self.quit(),
            width=12).grid(column=3, row=4, sticky="we")
        tk.Button(f, text="Save", command=lambda: self.ok("save"),
            width=12).grid(column=3, row=3, sticky="we")
        tk.Label(f, text="Data fields:").grid(column=0, row=self.line_no-1,
                sticky="nw")
        tk.Button(f, text="Add field", command=lambda: new_line(),
            width=12).grid(column=3, row=self.line_no-1, sticky="we")
        tk.Button(f, text="Load", command=lambda: self._update_fields(),
            width=12).grid(column=3, row=1, sticky="we")
        tk.Button(f, text="Update", command=lambda: self.ok("update"),
            width=12).grid(column=3, row=2, sticky="nwe")


    def ok(self, mode):


        data_fields = {
            self.elem_collection[keys][0].get(): eval(self.elem_collection[keys][1].get())
            for keys in self.elem_collection}

        values = {keys: self._get_val(self.form[keys][2][0]) for keys in self.form}
        values['data_dimension'] = 1
        values['data_fields'] = data_fields

        if mode == "save":
            try:
                self.conn.new_entry(Rtn, values)
            except sa.exc.InvalidRequestError, e:
                print ("Could not add the routine: \n\n{0}".format(e))
            except sa.exc.IntegrityError:
                tkMessageBox.showerror("Integrity Error", "A routine " +
                    "with that short name already exists.\n" +
                    "Please choose a different name.")
                self.form['alias'][2][0].focus_set()
        elif mode == "update":
            try:
                self.conn.update(self.conn.metadata.tables['routines'],
                    "alias",
                    self.form["alias"][2][0].get(),
                    values)

                db = values["alias"]
                db_fields = self.conn.metadata.tables[db].columns
                for keys in values["data_fields"]:
                    col = Column(keys, values["data_fields"][keys])
                    col.create(self.conn.metadata.tables[db])

            except sa.InvalidRequestError, e:
                print ("Could not update the routine: \n\n{0}".format(e))



    def _browse_sop(self):
        path = tkfd.askopenfilename(title="Select the SOP")
        self.form["sop"][2][0].delete(0, tk.END)
        self.form["sop"][2][0].insert(0, path)

    def _open_sop(self):

        def we_are_frozen():
            # All of the modules are built-in to the interpreter, e.g., by py2exe
            return hasattr(sys, "frozen")

        def module_path():
            encoding = sys.getfilesystemencoding()
            if we_are_frozen():
                return os.path.dirname(unicode(sys.executable, encoding))
            return os.path.dirname(unicode(__file__, encoding))

        filename = self.form["sop"][2][0].get()

        if sys.platform.startswith('darwin'):
            os.system("open " + filename)
        elif sys.platform.startswith('linux'):
            import subprocess
            subprocess.call(('xdg-open', filename))
        elif sys.platform.startswith('win32'):
            os.startfile(filename)




    def _update_fields(self):

        self.conn.metadata.reflect(self.conn.engine)
        name = self.form['alias'][2][0].get()
        col_names = [eval("Rtn.{0}".format(keys)) for keys in self.form]
        col_names.append(Rtn.data_fields)

        val = self.conn.session.query(*col_names).filter(Rtn.alias == name).first()
        col = self.form.keys()
        col.append("data_fields")

        dic = dict((key, value) for (key, value) in zip(col, val))
        for keys in self.form:
            if keys != "description":
                self.form[keys][2][0].delete(0, tk.END)
                if dic[keys]:
                    self.form[keys][2][0].insert(0, dic[keys])
            else:
                self.form[keys][2][0].delete("0.0", tk.END)
                if dic[keys]:
                    self.form[keys][2][0].insert("0.0", dic[keys])

        for keys in self.elem_collection:
            for elem in self.elem_collection[keys]:
                elem.destroy()
        self.elem_collection = {}
        line_no = len(self.form)+1
        for keys in dic["data_fields"]:
            elems = [
                tk.Label(self.f, justify=tk.LEFT, text=keys),
                tk.Label(self.f, justify=tk.LEFT, text=dic["data_fields"][keys])]
            for i in range(len(elems)):
                elems[i].grid(row=line_no, column=i+1, sticky="we")
            line_no += 1
        self.line_no = line_no

    def _get_val(self, obj):
        try:
            value = obj.get()
        except TypeError:
            value = obj.get(0.0, tk.END)
        return value

    def quit(self):
        self.parent.destroy()

class UsrMenu():

    def __init__(self, parent, conn):
        """The Main GUI"""

        self.parent = parent
        self.conn = conn
        usr_values = [re.sub(r'[^\x00-\x7f]',r'_',value[0])\
            for value in\
            self.conn.session.query(Usr.usr_name)\
            .distinct()]
        f = tk.Frame(self.parent, pady=5, padx=5)
        f.pack()
        self.form = collections.OrderedDict((
            ("usr_name", [
                "User name*:",
                tk.StringVar(),
                [ttk.Combobox(f, values=usr_values),]]),
            ("first_name", [
                "First name:",
                tk.StringVar(),
                [tk.Entry(f)],]),
            ("middle_name", [
                "Middle name:",
                tk.StringVar(),
                [tk.Entry(f)],]),
            ("last_name", [
                "Last name:",
                tk.StringVar(),
                [tk.Entry(f)],]),
            ("e_mail", [
                "E-mail:",
                tk.StringVar(),
                [tk.Entry(f),]]),
            ("affiliation", [
                "Affiliation:",
                tk.StringVar(),
                [tk.Entry(f),]]),
            ("degree", [
                "Degree:",
                tk.StringVar(),
                [tk.Entry(f),]]),
            ("phone", [
                "Phone:",
                tk.StringVar(),
                [tk.Entry(f),]]),
            ("working_directory", [
                "Working directory:",
                tk.StringVar(),
                [tk.Entry(f),
                tk.Button(f, text="Browse...",
                command=lambda: self.browse_dir())]])
        ))

        global line_no
        line_no = 1

        tk.Label(f, text="New user",
                font=("Helvetica", 14),
                pady=3,
                justify = "left").grid(row=0, column=0, columnspan=2, sticky="w")

        for keys in self.form:
            tk.Label(f, text=self.form[keys][0]).grid(row=line_no, column=0,
                sticky="nw")
            for i in range(len(self.form[keys][2])):
                self.form[keys][2][i].grid(row=line_no, column=1+i, sticky="we")
            line_no += 1
        self.elem_collection = {}
        tk.Button(f, text="Load", command=lambda: self._update_fields(),
            width=12).grid(column=2, row=1, sticky="we")
        tk.Button(f, text="Update", command=lambda: self.ok("update"),
            width=12).grid(column=2, row=2, sticky="we")
        tk.Button(f, text="Save", command=lambda: self.ok("save"),
            width=12).grid(column=2, row=3, sticky="we")
        tk.Button(f, text="Close", command=lambda: self.quit(),
            width=12).grid(column=2, row=4, sticky="we")

    def browse_dir(self):
        path = tkfd.askdirectory()
        self.form["working_directory"][2][0].delete(0, tk.END)
        self.form["working_directory"][2][0].insert(0, path)

    def _update_fields(self):

        self.conn.metadata.reflect(self.conn.engine)
        name = self.form['usr_name'][2][0].get()
        col_names = [eval("Usr.{0}".format(keys)) for keys in self.form]

        val = self.conn.session.query(*col_names).filter(Usr.usr_name == name).first()
        col = self.form.keys()

        dic = dict((key, value) for (key, value) in zip(col, val))
        for keys in self.form:
            self.form[keys][2][0].delete(0, tk.END)
            if dic[keys]:
                self.form[keys][2][0].insert(0, dic[keys])

    def _get_val(self, obj):
        try:
            value = obj.get()
        except TypeError:
            value = obj.get(0.0, tk.END)
        return value

    def ok(self, mode):

        values = {
            keys: self._get_val(self.form[keys][2][0]) for keys in self.form}
        if mode == "save":
            try:
                self.conn.new_entry(Usr, values)
            except sa.exc.InvalidRequestError, e:
                print ("Could not add the user: \n\n{0}".format(e))
            except sa.exc.IntegrityError:
                tkMessageBox.showerror("Integrity Error", "A user " +
                    "with that user name already exists.\n" +
                    "Please choose a different name.")
                self.form['usr_name'][2][0].focus_set()
        elif mode == "update":
            try:
                self.conn.update(self.conn.metadata.tables['users'],
                    "usr_name",
                    self.form["usr_name"][2][0].get(),
                    values)
            except sa.exc.InvalidRequestError, e:
                print ("Could not update the user: \n\n{0}".format(e))


    def quit(self):
        self.parent.destroy()

class CpdMenu():

    def __init__(self, parent, conn):
        """The Main GUI"""

        self.parent = parent
        self.conn = conn
        all_cpds = [re.sub(r'[^\x00-\x7f]',r'_',value[0])\
            for value in\
            self.conn.session.query(Cpd.name)\
            .distinct()]
        f = tk.Frame(self.parent, padx=5, pady=5)
        f.pack()
        self.form = collections.OrderedDict((
            ("name", [
                "Compound name/code*:",
                tk.StringVar(),
                [ttk.Combobox(f, values=all_cpds),]]),
            ("group", [
                "Compound group:",
                tk.StringVar(),
                [tk.Entry(f)],]),
            ("smiles", [
                "SMILES:",
                tk.StringVar(),
                [tk.Entry(f)],]),
            ("cas", [
                "CAS No.:",
                tk.StringVar(),
                [tk.Entry(f)],]),
            ("formula", [
                "Formula:",
                tk.StringVar(),
                [tk.Entry(f),]]),
            ("address", [
                "Origin:",
                tk.StringVar(),
                [tk.Entry(f),]]),
            ("batch", [
                "Batch-No.:",
                tk.StringVar(),
                [tk.Entry(f),]])
        ))

        global line_no
        line_no = 1

        tk.Label(f, text="New compound",
                font=("Helvetica", 14),
                pady=3,
                justify = "left").grid(row=0, column=0, columnspan=2, sticky="w")

        for keys in self.form:
            tk.Label(f, text=self.form[keys][0]).grid(row=line_no, column=0,
                sticky="nw")
            for i in range(len(self.form[keys][2])):
                self.form[keys][2][i].grid(row=line_no, column=1+i, sticky="we")
            line_no += 1
        self.elem_collection = {}



        tk.Button(f, text="Load", command=lambda: self._update_fields(),
            width=12).grid(column=3, row=1, sticky="we")
        tk.Button(f, text="Update", command=lambda: self.ok("update"),
            width=12).grid(column=3, row=2, sticky="we")
        tk.Button(f, text="Ok", command=lambda: self.ok(),
            width=12).grid(column=3, row=3, sticky="we")
        tk.Button(f, text="Close", command=lambda: self.quit(),
            width=12).grid(column=3, row=4, sticky="we")

    def _get_val(self, obj):
        try:
            value = obj.get()
        except TypeError:
            value = obj.get(0.0, tk.END)
        return value

    def _update_fields(self):

        self.conn.metadata.reflect(self.conn.engine)
        name = self.form['name'][2][0].get()
        col_names = [eval("Cpd.{0}".format(keys)) for keys in self.form]

        val = self.conn.session.query(*col_names).filter(Cpd.name == name).first()
        #col = self.conn.metadata.tables['users'].columns
        col = self.form.keys()

        dic = dict((key, value) for (key, value) in zip(col, val))
        #print dic
        for keys in self.form:
            self.form[keys][2][0].delete(0, tk.END)
            if dic[keys]:
                self.form[keys][2][0].insert(0, dic[keys])

    def ok(self, mode):

        values = {
            keys: self._get_val(self.form[keys][2][0]) for keys in self.form}
        if mode == "save":
            try:
                self.conn.new_entry(Cpd, values)
            except sa.InvalidRequestError, e:
                print ("Could not add the compound: \n\n{0}".format(e))
            except sa.IntegrityError:
                tkMessageBox.showerror("Integrity Error", "A compound " +
                    "with that name already exists.\n" +
                    "Please choose a different name.")
                self.form['name'][2][0].focus_set()
        elif mode == "update":
            try:
                self.conn.update(self.conn.metadata.tables['compounds'],
                    "name",
                    self.form["name"][2][0].get(),
                    values)
            except sa.InvalidRequestError, e:
                print ("Could not update the compound: \n\n{0}".format(e))


    def quit(self):
        self.parent.destroy()

class ListMenu():

    def __init__(self, parent, df):
        """The Main GUI"""

        self.parent = parent
        self.df = df
        f = tk.Frame(self.parent)
        f.pack()
        text_area = ScrolledText(f, width=100, height=50, wrap=tk.NONE)
        text_area.insert(tk.INSERT, df)
        text_area.grid(column=0, row=2, columnspan=5)



        tk.Button(f, text="Close", command=lambda: self.quit(),
            width=12).grid(column=4, row=1, sticky="we")
        tk.Button(f, text="Save as...", command=lambda: self.save(),
            width=12).grid(column=3, row=1, sticky="we")


    def save(self, format="txt"):
        f = tkfd.asksaveasfile(mode='w', defaultextension="txt",
            title="Save file as...")
        if f:
            try:
                f.write(self.df)
            except UnicodeEncodeError:
                tkMessageBox.showerror("Encoding problem",
                    "> Could not save file due to unsupported special" +
                    "characters.\n\n" +
                    "Original message:\n {0}".format(e))
            f.close()

    def quit(self):
        self.parent.destroy()

class PreviewDialog:

    def __init__(self, parent, df):

        top = self.top = tk.Toplevel(parent)

        tk.Label(top, text="This is how your data will be sent to the " +
            "database.\nClick 'Accept' to proceed or 'Discard' to " +
            "cancel").grid(row=1, column=0, columnspan=5)

        text_area = ScrolledText(top, width=100, height=50, wrap=tk.NONE)
        text_area.insert(tk.INSERT, df)
        text_area.grid(column=0, row=2, columnspan=5)



        tk.Button(top, text="Accept", command=self.ok).grid(row=3,
            column=0, sticky="we")
        tk.Button(top, text="Discard", command=self.quit).grid(row=3,
            column=1, sticky="we")

    def ok(self):

        self.result = True
        self.top.destroy()

    def quit(self):

        self.result = False
        self.top.destroy()


def _get_rtn_files(obj):
    """ Write the Template file to the user directory.

    Arguments:
    obj -- The routine class for which the script is intended.
    """

    tbl_template = ["$$res_tbl['{0}'] = ".format(field)
                    for field in obj.data_fields]
    template = """
# Template for data import and export functions. You can modify this file
# to fit your needs, however:
# - Do not change the names of the functions, as they will be called from the
#   module;
# - Make sure that the return values from get_data() are in the right format

# Uncomment if you need functions from the aux_func module.

#from screening_management  import aux_func

# These modules are used in the template:

from matplotlib import pyplot as pl
from matplotlib import rcParams
import numpy as np
import pandas, math

# This function is called when entering new data:
# The function is called with *args, **kwargs, so you can specify any
# arguments you need. Examples are provided in the "examples" folder.

def get_data(load_range = range(1,137), newer_than=0, plate_size=96):
$"Loads and processes the raw data and returns it to be inserted into the database"

$# Use this loop if you want to process multiple assays at a time
$results = []
$for assay in assays:

$$# Create a pandas Data frame to collect the data. More information about
$$# the pandas module can be found here:
$$# http://pandas.pydata.org/pandas-docs/stable/index.html
$$#
$$# It is recommended to insert a column with the samples, as well as one
$$# for each plate.
$$#
$$# | Sample$| Plate 0   | Plate 1$| ...
$$# +-----------+-----------+------------+----
$$# | Sample 1  | 0.001$ | 0.002$  | ...
$$# | Sample 1  | 0.002$ | 0.004$  | ...
$$# | Sample 2  | 0.003$ | 0.008$  | ...
$$# | ...$   | ...$   | ...$$| ...
$$#
$$df = pandas.DataFrame(data = "", columns = ["Sample", "Plate 0", "Plate 1"])

$$# Outlier detection?
$$gd = df.groupby("Sample")$ # Group the data frame
$$res_tbl = pandas.DataFrame()  # Create an empty data frames to collect results
$$
$$# Make sure to provide valselfues for all the required fields
{0}
$$# Do not change this dictionary except for the date and the sample!
$$# (Unless you know
$$# what you're doing)
$$meta_values = {{
$$$"user": "{1}",
$$$"routine": "{2}",
$$$"date": ,
$$$"sample": ,
$$$"active": 1}}


$$results.append([res_tbl, meta_values])
$
$# Data format:
$#
$# [[res_tbl_0, meta_values_0],
$#  [res_tbl_1, meta_values_1],
$#  ...
$#  [res_tbl_n, meta_values_n]]
$#
$# where res_tbl are data frames and meta values are dicts.
$# If large quantities of data are important, consider a generator, or limit
$# the assays to be imported at once.
$
$return results


# This function is called when the user wants to get the results as a list,
# either do be displayed on screen or printed into a file. "data" is a pandas
# data frame.

def summarize_list(data, *args, **kwargs):
$"Summarizes the data as a list"

$column_header = ('Column 1', 'Column 2', 'Column n')
$df = pandas.DataFrame(columns = column_header)
$# Select the data and format you want to display
$df['Column 1'] = ["{{0:<10s}}".format(y) for y in data['Col1']]
$df['Column 2'] = ["{{0:<10s}}".format(y) for y in data['Col2']]
$df['Column 3'] = ["{{0:<10s}}".format(y) for y in data['Col3']]
$
$df_sorted = df.sort(columns=['Column 1', 'Column 2'])
$return df_sorted.to_string(justify='left')

usr_path
# This function is called when the user wants to display or save a plot.
# It recieves the same arguments as summarize_list().

def summarize_plot(data_unsorted, *args, **kwargs):
$"Plots the data"

$no_plots = 1 # The number of subplots to be drawn
$
$# Some plot settings
$pl.rc('text', usetex=False)
$pl.rc('font', family='serif')rs-in-python-string-and-also-use-format
$pl.figure(facecolor="white", figsize=(12, (math.ceil(no_plots/2))*10), dpi=80)
$pl.subplots_adjust(wspace = 0.9, hspace = 0.9)
$rcParams.update({{'figure.autolayout': True}})
$
$# Produces a subplot
$for i in range(0, no_plots):
$$
$$x_values = []
$$number_of_datapoints = len(x_values)
$$error_bars = []
$$x_labels = []
$$x = np.linspace(1, number_of_datapoints, number_of_datapoints)
$$pl.subplot(math.ceil(no_plots*0.5), 2, i+1)
$$pl.bar(x-0.4, x_values,  0.8, color="#AAAAAA", edgecolor="black",
$$$yerr=error_bars, ecolor="black", capsize=8)

$$# Set x limits
$$pl.xlim(0+0.5, number_of_datapoints+0.5)

$$# Set x ticks
$$pl.xticks(x, x_labels, size="small", rotation=90)

$$# Set y limits
$$pl.ylim(min(x_values)*1.1, max(x_values)*1.2)

$$# Set y ticks
$$tick_pos = np.linspace(0, 1, 5, endpoint=True)
$$pl.yticks(tick_pos,["{{0:.0%}}".format(tick) for tick in tick_pos])

$$pl.ylabel('X-Values')
$$pl.xlabel('Sample')
$$pl.title('Title')
$$
$return pl

""".format("\n".join(tbl_template), obj.author, obj.alias)
    f = open("{0}/{1}.py".format(obj.usr_dir[0], obj.alias), "w")
    f.write(template.replace("$", "    "))
    f.close()

def auto(*args, **kwargs):
    """ """
    pass

def console(*args, **kwargs):
    """ Start rudimentary command line style user interface."""

    # To do: input mask for new connection

    CmdLine().cmdloop(intro="Command line input. Press '?' for help, 'exit' to quit")


def gui(*args, **kwargs):
    """Start the GUI"""

    root = tk.Tk()
    root.title('Database connection')
    connection_dlg = DB_connection(root)
    root.wait_window(connection_dlg.parent)
    return True

def function1(self, arg1, arg2, arg3):
    """
    returns (arg1 / arg2) + arg3

    This is a longer explanation, which may include math with latex syntax
    :math:`\\alpha`.
    Then, you need to provide optional subsection in this order (just to be
    consistent and have a uniform documentation. Nothing prevent you to
    switch the order):

        - parameters using ``:param <name>: <description>``
        - type of the parameters ``:type <name>: <description>``
        - returns using ``:returns: <description>``
        - examples (doctest)
        - seealso using ``.. seealso:: text``
        - notes using ``.. note:: text``
        - warning using ``.. warning:: text``
        - todo ``.. todo:: text``

    **Advantages**:
        - Uses sphinx markups, which will certainly be improved in future
        version
        - Nice HTML output with the See Also, Note, Warnings directives


    **Drawbacks**:
        - Just looking at the docstring, the parameter, type and  return
        sections do not appear nicely

    :param arg1: the first value
    :param arg2: the first value
    :param arg3: the first value
    :type arg1: int, float,...
    :type arg2: int, float,...
    :type arg3: int, float,...
    :returns: arg1/arg2 +arg3
    :rtype: int, float

    :Example:

    >>> import template
    >>> a = template.MainClass1()
    >>> a.function1(1,1,1)
    2

    .. note:: can be useful to emphasize
        important feature
    .. seealso:: :class:`MainClass2`
    .. warning:: arg2 must be non-zero.
    .. todo:: check that arg2 is non zero.
    """

    return arg1/arg2 + arg3
