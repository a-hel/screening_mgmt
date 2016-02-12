============
Introduction
============

The module *screening_mgmt* is a light-weight interface to read data files from measurement devices and store the results in a sql type database. It was developed for in-house use and as such adapted to the workflow and equipment from our research group. However, it is flexible enough to be tuned in for similar applications.

Its main task is to handle results from various bioactivity screening assays. It reads the raw readout file and aggregates the data by compound name, assay and user, thus taking advantage of sql's relational features. Pre- and post-import hooks allow data processing before storing it in the database or before displaying it on screen.

Structure
---------

The module contains two layers of interaction: The lower level provides an API to common tasks like reading, writing and setting up the database. It also provides hooks for pre- and post-import scripts. These functions can be accessed like a normal *Python* module.

The higher level provides a GUI directed towards users with no programming experience.

For common maintenance and debugging tasks, there is also a small command line tool.