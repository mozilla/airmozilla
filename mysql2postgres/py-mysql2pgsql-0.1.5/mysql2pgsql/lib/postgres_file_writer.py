from __future__ import absolute_import

import time


from .postgres_writer import PostgresWriter

from . import print_row_progress, status_logger


class PostgresFileWriter(PostgresWriter):
    """Class used to ouput the PostgreSQL
    compatable DDL and/or data to the specified
    output :py:obj:`file` from a MySQL server.

    :Parameters:
      - `output_file`: the output :py:obj:`file` to send the DDL and/or data
      - `verbose`: whether or not to log progress to :py:obj:`stdout`

    """
    verbose = None

    def __init__(self, output_file, verbose=False):
        super(PostgresFileWriter, self).__init__()
        self.verbose = verbose
        self.f = output_file
        self.f.write("""
-- MySQL 2 PostgreSQL dump\n
SET client_encoding = 'UTF8';
SET standard_conforming_strings = off;
SET check_function_bodies = false;
SET client_min_messages = warning;
""")

    @status_logger
    def truncate(self, table):
        """Write DDL to truncate the specified `table`

        :Parameters:
          - `table`: an instance of a :py:class:`mysql2pgsql.lib.mysql_reader.MysqlReader.Table` object that represents the table to read/write.

        Returns None
        """
        truncate_sql, serial_key_sql = super(PostgresFileWriter, self).truncate(table)
        self.f.write("""
-- TRUNCATE %(table_name)s;
%(truncate_sql)s
""" % {'table_name': table.name, 'truncate_sql': truncate_sql})

        if serial_key_sql:
            self.f.write("""
%(serial_key_sql)s
""" % {
    'serial_key_sql': serial_key_sql})

    @status_logger
    def write_table(self, table):
        """Write DDL to create the specified `table`.

        :Parameters:
          - `table`: an instance of a :py:class:`mysql2pgsql.lib.mysql_reader.MysqlReader.Table` object that represents the table to read/write.

        Returns None
        """
        table_sql, serial_key_sql = super(PostgresFileWriter, self).write_table(table)
        if serial_key_sql:
            self.f.write("""
%(serial_key_sql)s
""" % {
    'serial_key_sql': '\n'.join(serial_key_sql)
    })

        self.f.write("""
-- Table: %(table_name)s
%(table_sql)s
""" % {
    'table_name': table.name,
    'table_sql': '\n'.join(table_sql),
    })

    @status_logger
    def write_indexes(self, table):
        """Write DDL of `table` indexes to the output file

        :Parameters:
          - `table`: an instance of a :py:class:`mysql2pgsql.lib.mysql_reader.MysqlReader.Table` object that represents the table to read/write.

        Returns None
        """
        self.f.write('\n'.join(super(PostgresFileWriter, self).write_indexes(table)))

    @status_logger
    def write_constraints(self, table):
        """Write DDL of `table` constraints to the output file

        :Parameters:
          - `table`: an instance of a :py:class:`mysql2pgsql.lib.mysql_reader.MysqlReader.Table` object that represents the table to read/write.

        Returns None
        """
        self.f.write('\n'.join(super(PostgresFileWriter, self).write_constraints(table)))

    @status_logger
    def write_contents(self, table, reader):
        """Write the data contents of `table` to the output file.

        :Parameters:
          - `table`: an instance of a :py:class:`mysql2pgsql.lib.mysql_reader.MysqlReader.Table` object that represents the table to read/write.
          - `reader`: an instance of a :py:class:`mysql2pgsql.lib.mysql_reader.MysqlReader` object that allows reading from the data source.

        Returns None
        """
        # start variable optimiztions
        pr = self.process_row
        f_write = self.f.write
        verbose = self.verbose
        # end variable optimiztions

        f_write("""
--
-- Data for Name: %(table_name)s; Type: TABLE DATA;
--

COPY "%(table_name)s" (%(column_names)s) FROM stdin;
""" % {
                'table_name': table.name,
                'column_names': ', '.join(('"%s"' % col['name']) for col in table.columns)})
        if verbose:
            tt = time.time
            start_time = tt()
            prev_val_len = 0
            prev_row_count = 0
        for i, row in enumerate(reader.read(table), 1):
            row = list(row)
            pr(table, row)
            try:
                f_write(u'%s\n' % (u'\t'.join(row)))
            except UnicodeDecodeError:
                f_write(u'%s\n' % (u'\t'.join(r.decode('utf-8') for r in row)))
            if verbose:
                if (i % 20000) == 0:
                    now = tt()
                    elapsed = now - start_time
                    val = '%.2f rows/sec [%s] ' % ((i - prev_row_count) / elapsed, i)
                    print_row_progress('%s%s' % (("\b" * prev_val_len), val))
                    prev_val_len = len(val) + 3
                    start_time = now
                    prev_row_count = i

        f_write("\\.\n\n")
        if verbose:
            print('')

    def close(self):
        """Closes the output :py:obj:`file`"""
        self.f.close()
