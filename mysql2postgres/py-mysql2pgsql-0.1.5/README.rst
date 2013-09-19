========================================================================================
py-mysql2pgsql - A tool for migrating/converting/exporting data from MySQL to PostgreSQL
========================================================================================

This tool allows you to take data from an MySQL server (only tested on
5.x) and write a PostgresSQL compatable (8.2 or higher) dump file or pipe it directly
into your running PostgreSQL server (8.2 or higher).

.. attention::
   Currently there is no support for importing `spatial data from MySQL
   <http://dev.mysql.com/doc/refman/5.5/en/spatial-extensions.html>`_.


Installation:
=============

If you're like me you don't like random stuff polluting your python
install. Might I suggest installing this in an virtualenv?

::

    > virtualenv --no-site-packages ~/envs/py-mysql2pgsql
    > source ~/envs/py-mysql2pgsql/bin/activate


Requirements:
-------------

* `Python 2.6 or 2.7 <http://www.python.org/getit/>`_
* `MySQL-python <http://pypi.python.org/pypi/MySQL-python>`_
* `psycopg2 <http://pypi.python.org/pypi/psycopg2>`_
* `PyYAML <http://pypi.python.org/pypi/PyYAML>`_
* `termcolor <http://pypi.python.org/pypi/termcolor>`_ (unless you're installing on windows)


On Windows
----------

I have only done limited testing on this platform using Python
2.7. Here are the driver dependencies for windows, install these
before attempting to install py-mysql2pgsql or it will fail.

* `psycopg2 for Windows <http://www.stickpeople.com/projects/python/win-psycopg/>`_
* `MySQL-python for Windows <http://www.codegood.com/archives/129>`_



From PyPI:
----------

All dependencies **should** be automatically installed when installing
the app the following ways

::

    > pip install py-mysql2pgsql


From source:
------------

::

    > git clone git://github.com/philipsoutham/py-mysql2pgsql.git
    > cd py-mysql2pgsql
    > python setup.py install


Usage:
======

Looking for help?

::

    > py-mysql2pgsql -h
    usage: py-mysql2pgsql [-h] [-v] [-f FILE]

    Tool for migrating/converting data from mysql to postgresql.

    optional arguments:
      -h, --help            show this help message and exit
      -v, --verbose         Show progress of data migration.
      -f FILE, --file FILE  Location of configuration file (default:
                            mysql2pgsql.yml). If none exists at that path,
                            one will be created for you.
                        

Don't worry if this is your first time, it'll be gentle.

::

    > py-mysql2pgsql
    No configuration file found.
    A new file has been initialized at: mysql2pgsql.yml
    Please review the configuration and retry...

As the output suggests, I file was created at mysql2pgsql.yml for you
to edit. For the impatient, here is what the file contains.

::

    # if a socket is specified we will use that
    # if tcp is chosen you can use compression
    mysql:
     hostname: localhost
     port: 3306
     socket: /tmp/mysql.sock
     username: mysql2psql
     password: 
     database: mysql2psql_test
     compress: false
    destination:
     # if file is given, output goes to file, else postgres
     file: 
     postgres:
      hostname: localhost
      port: 5432
      username: mysql2psql
      password: 
      database: mysql2psql_test

    # if only_tables is given, only the listed tables will be converted.  leave empty to convert all tables.
    #only_tables:
    #- table1
    #- table2
    # if exclude_tables is given, exclude the listed tables from the conversion.
    #exclude_tables:
    #- table3
    #- table4

    # if supress_data is true, only the schema definition will be exported/migrated, and not the data
    supress_data: false

    # if supress_ddl is true, only the data will be exported/imported, and not the schema
    supress_ddl: false

    # if force_truncate is true, forces a table truncate before table loading
    force_truncate: false


Pretty self explainitory right? A couple things to note, first if
`destination -> file` is populated all outpute will be dumped to the
specified location regardless of what is contained in `destination ->
postgres`. So if you want to dump directly to your server make sure
the `file` value is blank.

Say you have a MySQL db with many, many tables, but you're only
interested in exporting a subset of those table, no problem. Add only
the tables you want to include in `only_tables` or tables that you
don't want exported to `exclude_tables`. 

Other items of interest may be to skip moving the data and just create
the schema or vice versa. To skip the data and only create the schema
set `supress_data` to `true`. To migrate only data and not recreate the
tables set `supress_ddl` to `true`; if there's existing data that you
want to drop before importing set `force_truncate` to
`true`. `force_truncate` is not necessary when `supress_ddl` is set to
`false`.

One last thing, the `--verbose` flag. Without it the tool will just go
on it's merry way without bothering you with any output until it's
done. With it you'll get a play-by-play summary of what's going
on. Here's an example.

::

    > py-mysql2pgsql -v -f mysql2pgsql
    START PROCESSING table_one
      START  - CREATING TABLE table_one
      FINISH - CREATING TABLE table_one
      START  - WRITING DATA TO table_one
      24812.02 rows/sec [20000]  
      FINISH - WRITING DATA TO table_one
      START  - ADDING INDEXES TO table_one
      FINISH - ADDING INDEXES TO table_one
      START  - ADDING CONSTRAINTS ON table_one
      FINISH - ADDING CONSTRAINTS ON table_one
    FINISHED PROCESSING table_one

    START PROCESSING table_two
      START  - CREATING TABLE table_two
      FINISH - CREATING TABLE table_two
      START  - WRITING DATA TO table_two

      FINISH - WRITING DATA TO table_two
      START  - ADDING INDEXES TO table_two
      FINISH - ADDING INDEXES TO table_two
      START  - ADDING CONSTRAINTS ON table_two
      FINISH - ADDING CONSTRAINTS ON table_two
    FINISHED PROCESSING table_two


Data Type Conversion Legend
===========================

Since there is not a one-to-one mapping between MySQL and
PostgreSQL data types, listed below are the conversions that are applied. I've
taken some liberties with some, others should come as no surprise.

==================== ===========================================
MySQL                PostgreSQL
==================== ===========================================
char                 character
varchar              character varying
tinytext             text
mediumtext           text
text                 text
longtext             text
tinyblob             bytea
mediumblob           bytea
blob                 bytea
longblob             bytea
binary               bytea
varbinary            bytea
bit                  bit varying
tinyint              smallint
tinyint unsigned     smallint
smallint             smallint
smallint unsigned    integer
mediumint            integer
mediumint unsigned   integer
int                  integer
int unsigned         bigint
bigint               bigint
bigint unsigned      numeric
float                real
float unsigned       real
double               double precision
double unsigned      double precision
decimal              numeric
decimal unsigned     numeric
numeric              numeric
numeric unsigned     numeric
date                 date
datetime             timestamp without time zone
time                 time without time zone
timestamp            timestamp without time zone
year                 smallint
enum                 character varying (with `check` constraint)
set                  ARRAY[]::text[]
==================== ===========================================


About:
======

I ported much of this from an existing project written in Ruby by Max
Lapshin over at `<https://github.com/maxlapshin/mysql2postgres>`_. I
found that it worked fine for most things, but for migrating large tables
with millions of rows it started to break down. This motivated me to
write *py-mysql2pgsql* which uses a server side cursor, so there is no "paging"
which means there is no slow down while working it's way through a
large dataset.
