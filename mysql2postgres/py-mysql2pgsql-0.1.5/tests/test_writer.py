from __future__ import with_statement, absolute_import
import os
import sys
import re
import tempfile
import unittest

from . import WithReader

sys.path.append(os.path.abspath('../'))

from mysql2pgsql.lib.postgres_writer import PostgresWriter
from mysql2pgsql.lib.postgres_file_writer import PostgresFileWriter
from mysql2pgsql.lib.postgres_db_writer import PostgresDbWriter

def squeeze(val):
    return re.sub(r"[\x00-\x20]+", " ", val).strip()
        
class WithTables(WithReader):
    def setUp(self):
        super(WithTables, self).setUp()
        self.table1 = next((t for t in self.reader.tables if t.name == 'type_conversion_test_1'), None)
        self.table2 = next((t for t in self.reader.tables if t.name == 'type_conversion_test_2'), None)
        assert self.table1
        assert self.table2


class TestPostgresWriter(WithTables):
    def setUp(self):
        super(self.__class__, self).setUp()
        self.writer = PostgresWriter()
        assert self.writer
        
    def test_truncate(self):
        trunc_cmds = self.writer.truncate(self.table1)
        assert len(trunc_cmds) == 2
        trunc_stmt, reset_seq = trunc_cmds
        assert squeeze(trunc_stmt) == 'TRUNCATE "%s" CASCADE;' % self.table1.name
        if reset_seq:
            self.assertRegexpMatches(squeeze(reset_seq),
                                 "^SELECT pg_catalog.setval\(pg_get_serial_sequence\('%s', 'id'\), \d+, true\);$" % self.table1.name)

    def test_write_table(self):
        write_table_cmds = self.writer.write_table(self.table1)
        assert len(write_table_cmds) == 2
        table_cmds, seq_cmds = write_table_cmds
        assert len(table_cmds) == 2
        assert squeeze(table_cmds[0]) == 'DROP TABLE IF EXISTS "%s" CASCADE;' % self.table1.name
        assert 'CREATE TABLE "%s"' % self.table1.name in table_cmds[1]
#        assert self.assertRegexpMatches(squeeze(table_cmds[1]),
#                                        '^CREATE TABLE "%s" \(.*\) WITHOUT OIDS;$' % self.table1.name)

        if seq_cmds:
            assert len(seq_cmds) == 3
            self.assertRegexpMatches(squeeze(seq_cmds[0]),
                                     '^DROP SEQUENCE IF EXISTS %s_([^\s]+)_seq CASCADE;$' % self.table1.name)
            self.assertRegexpMatches(squeeze(seq_cmds[1]),
                                     '^CREATE SEQUENCE %s_([^\s]+)_seq INCREMENT BY 1 NO MAXVALUE NO MINVALUE CACHE 1;$' % self.table1.name)
            self.assertRegexpMatches(squeeze(seq_cmds[2]),
                                     "^SELECT pg_catalog.setval\('%s_([^\s]+)_seq', \d+, true\);$" % self.table1.name)

    def test_write_indexex(self):
        index_cmds = self.writer.write_indexes(self.table1)
        assert len(index_cmds) == 9
        
    def test_write_constraints(self):
        constraint_cmds = self.writer.write_constraints(self.table2)
        assert constraint_cmds


class WithOutput(WithTables):

    def setUp(self):
        super(WithOutput, self).setUp()

    def tearDown(self):
        super(WithOutput, self).tearDown()



class TestPostgresFileWriter(WithOutput):
    def setUp(self):
        super(self.__class__, self).setUp()
        self.outfile = tempfile.NamedTemporaryFile()
        self.writer = PostgresFileWriter(self.outfile)

    def tearDown(self):
        super(self.__class__, self).tearDown()
        self.writer.close()

    def test_truncate(self):
        self.writer.truncate(self.table1)

    def test_write_table(self):
        self.writer.write_table(self.table1)

    def test_write_indexes(self):
        self.writer.write_indexes(self.table1)

    def test_write_constraints(self):
        self.writer.write_constraints(self.table2)

    def test_write_contents(self):
        self.writer.write_contents(self.table1, self.reader)


class TestPostgresDbWriter(WithOutput):
    def setUp(self):
        super(self.__class__, self).setUp()
        self.writer = PostgresDbWriter(self.config.options['destination']['postgres'], True)
    def tearDown(self):
        super(self.__class__, self).tearDown()
        self.writer.close()

    def test_truncate(self):
        self.writer.truncate(self.table1)

    def test_write_table_indexes_and_constraints(self):
        self.writer.write_table(table=self.table1)
        self.writer.write_indexes(self.table1)
        self.writer.write_constraints(self.table2)

    def test_write_contents(self):
        self.writer.write_contents(self.table1, self.reader)
