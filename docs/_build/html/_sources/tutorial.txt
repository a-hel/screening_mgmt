========
Tutorial
========

Using the module
----------------

First, you need to initialize a :py:class:`DbConnection` object, specifying the necessary parameters to connect to your database:

>>> import screening_mgmt as sm
>>> sm.DbConnection(dialect, host, user, pw, db, driver=None, key_val=None)

The module uses SQLAlchemy to communicate with the database. At the moment, it supports the following dialects:

| "Drizzle": "drizzle",
| "Firebird": "firebird",
| "Microsoft SQL Server": "mssql",
| "MySQL": "mysql",
| "Oracle": "oracle",
| "PostgreSQL": "postgresql",
| "SQLite": "sqlite",
| "Sybase": "sybase"

.. warning:: The module has only been tested with *SQLite*, *MySQL* and *Microsoft SQL Server*.

Structure
---------

*Screening_mgmt* is an interface to integarate your data handling routines with your SQL database. It links raw data to (pre-)processing routines and automatizes data storage. It is designed to help people unfamiliar with the screening assays to quickly process store measurement data and look at results.

It offeres a quick way to organize, store and retreive data from screening assays. On initialization, it creates seperate data tables for the screened compounds, the users and the measurement routines. Upon import of new data, it automatically updates 


Security
--------

.. warning:: *screening_mgmt* is in no way a security layer for your database. It should only be used by people who have access to the database anyway. It does not provide any secure connection to the database nor is it protected against SQL injections or similar security risks.

Prerequisites
-------------

.. note:: If you just use this module to visualize existing results, you can skip ahead to the *GUI* section.

In order to work properly, you first need a database, where you can store your results.

You need a so-called *routine* script to tell the program how to handle your data. Instructions on how to write such a script can be found in the following paragraph.

Preparing the routine
---------------------

For each assay type, you can specify one or several routines. These are regular *Python* scripts with the following features:

.. code-block:: python

	from matplotlib import pyplot as pl
	from matplotlib import rcParams
	import numpy as np
	import pandas, math

	def get_data(load_range = range(1,100), newer_than=0, plate_size=96):
		"""
		This function is called when you add new data. You can use
		load_range and newer_than arguments to limit the records you wish
		to import.
		Aggregate your data in a pandas dataframe.
		Create a dictionary with the meta tags for your data record, so 
		it will be stored correctly in the database.
		Return the dataframe and the dictionary as a tuple"""

		results = pandas.DataFrame()  # Create an empty data frames to collect results

		meta_values = {
			"user": <user_name>,
			"routine": <routine_name>,
			"date": ,
			"sample": ,
			"active": 1}

		return (results, meta_values)

	def summarize_list(data, *args, **kwargs):
		"""
		This function is called when you display your data in list format.
		It receives a pandas.DataFrame and returns a string.
		"""

		return data.to_string(justify='left')

	def summarize_plot(data, *args, **kwargs):
		"""
		This function is called when you display your data as a plot.
		It receives a pandas.DataFrame and returns a matplotlib object.
		"""
	
		return data.plot()

GUI
---

The easiest way to use *screening_mgmt* is through its GUI, which is started as follows:

>>> import screening_mgmt as sm
>>> sm.gui()

This first opens the connection dialog, which allows you to connect to an existing database.

After succesful connection, the main menu is displayed.

- Query tab: Here, you can access the data in your database through the query builder. A click on the 'Preview' button shows the SQL command that will be sent to the server. If you have the right routines set up, you can present the retrieved results as table or as graph.

- Manage tab: Manually add and modify routines, users and compounds. You can batch import records through csv files.

- Add tab: Add new data, either with an existing routine or by adding a new one. You can choose, which records you want to import by entering row numbers or a date. If your routine supports other arguments, you can specify them in the 'keywords' field.

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

|**usr <user_name>**: Add a new user to the database
|**init**: Initialize the database and build the underlying structure
|**reset**: Deletes (drops) all tables and re-initializes the database.
Warning: This step is irreversible!
|**exe <command>**: Execute raw SQL command.
|**summary [<table>]**: Shows a list of all tables in the database. If a table name is given, also shows all the columns of that table.
|**enter <routine>**: Load data according to the specified routine.
|**close**: Close the connection.
|**gui**: Start the module in graphical mode
|**exit**: Quits the console
