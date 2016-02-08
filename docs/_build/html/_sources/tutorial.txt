========
Tutorial
========

Using the module
----------------

First, you need to initialize a :py:class DbConnection object, specifying the necessary parameters to connect to your database:

>>> import screening_mgmt as sm
>>> sm.DbConnection(dialect, host, user, pw, db, driver=None, key_val=None)

The module uses SQLAlchemy to communicate with the database. At the moment, it supports the following dialects:

"Drizzle": "drizzle",
"Firebird": "firebird",
"Microsoft SQL Server": "mssql",
"MySQL": "mysql",
"Oracle": "oracle",
"PostgreSQL": "postgresql",
"SQLite": "sqlite",
"Sybase": "sybase"

Structure
---------


Security
--------


GUI
---

Download the module from *GitHub*: `github.com/a-hel/screening_mgmt <https://github.com/a-hel/screening_mgmt/>`_.

Command line
------------

The module provides a small command line-style interface. It is intended mainly for maintenance and debugging tasks.
To start in command line mode, simply call

>>> import screening_mgmt as sm
>>> sm.console()

The program will then prompt you to create a new connection by entering 'n'.
If you already have connected to a database before, it will list the previous connections.
Follow the intructions on the screen in order to set up the connection.

Once the connection is established, you get access to the following functions:

**usr <user_name>**: Add a new user to the database
**init**: Initialize the database and build the underlying structure
**reset**: Deletes (drops) all tables and re-initializes the database.
Warning: This step is irreversible!
**exe <command>**: Execute raw SQL command.
**summary [<table>]**: Shows a list of all tables in the database. If a table name is given, also shows all the columns of that table.
**load**: 
**enter <routine>**: Load data according to the specified routine.
**close**: Close the connection.
**gui**: Start the module in graphical mode
**exit**: Quits the console
