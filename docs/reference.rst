=========
Reference
=========

Functions
---------
.. automodule:: screening_mgmt.screening_mgmt
   :members:

xzy

.. autofunction:: screening_mgmt
    :members:

Classes
-------

xyz

:py:class:: DbConnection()

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

.. autoclass:: screening_mgmt.screening_mgmt.DbConnection

