============
Introduction
============

The module *screening_mgmt* is a light-weight interface to read data files from measurement devices and store the results in a sql type database. It is mainly designed to handle results from various screening assays carried out on a set of compounds, aggregating the data by compound name, assay and user and taking advantage of sql's relational features.

Structure
---------

The module is structured into three layers: The middle level provides an API to common tasks like reading, writing and setting up the database. It also provides hooks for pre- and post-import scripts. These functions can be accessed like a normal *Python* module.

The highest level provides both a GUI and a command line interface directed towards users with no programming experience.