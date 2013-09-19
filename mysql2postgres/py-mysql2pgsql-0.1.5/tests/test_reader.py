from __future__ import with_statement
import sys
import os
import unittest

from contextlib import closing

import MySQLdb

sys.path.append(os.path.abspath('../'))

from mysql2pgsql.lib.config import Config
from mysql2pgsql.lib.mysql_reader import MysqlReader
from mysql2pgsql.lib.errors import ConfigurationFileNotFound

class TestMysqlReader(unittest.TestCase):
    def setUp(self):
        try:
            self.config_file = os.path.join(os.path.dirname(__file__), 'mysql2pgsql-test.yml')
            config = Config(self.config_file, False)
        except ConfigurationFileNotFound:
            print("In order to run this test you must create the file %s" % config)
            sys.exit(-1)
        self.options = config.options['mysql']

        self.args = {            
            'user': self.options.get('username', 'root'),
            'db': self.options['database'],
            'use_unicode': True,
            'charset': 'utf8',
            }

        if self.options.get('password', None):
            self.args['passwd'] = self.options.get('password', None)

        if self.options.get('socket', None):
            self.args['unix_socket'] = self.options['socket']
        else:
            self.args['host'] = self.options.get('hostname', 'localhost')
            self.args['port'] = self.options.get('port', 3306)
            self.args['compress'] = self.options.get('compress', True)

        with open(os.path.join(os.path.dirname(__file__), 'schema.sql')) as sql:
            self.sql = sql.read()
            with closing(MySQLdb.connect(**self.args)) as conn:
                with closing(conn.cursor()) as cur:
                    for cmd in self.sql.split('-- SPLIT'):
                        cur.execute(cmd)
                        conn.commit()
        self.reader = MysqlReader(self.options)
        self.type_to_pos = {
            'text': (21, 22),
            'float': (83, 84, 85, 86, 87, 88, 89, 90),
            'numeric': (75, 76, 77, 78),
            'datetime': (113, 114, 115, 116, 117, 118),
            'char': (9, 10, 11, 12),
            'boolean': (49, 50),
            "enum('small','medium','large')": (1, 2, 3, 4),
            'bit(8)': (37, 38, 39, 40),
            'mediumblob': (27, 28),
            'mediumtext': (19, 20),
            'blob': (29, 30),
            "set('a','b','c','d','e')": (5, 6, 7, 8),
            'varchar': (13, 14, 15, 16),
            'timestamp': (125, 126, 127, 128, 129, 130),
            'binary(3)': (33, 34),
            'varbinary(50)': (35, 36),
            'date': (107, 108, 109, 110, 111, 112),
            'integer': (0, 51, 52, 53, 54, 59, 60, 61, 62, 63, 64, 65, 66, 71, 72, 73, 74),
            'double precision': (91, 92, 93, 94, 95, 96, 97, 98),
            'tinytext': (17, 18),
            'decimal': (99, 100, 101, 102, 103, 104, 105, 106, 136, 137, 138, 139, 140, 141, 142, 143),
            'longtext': (23, 24),
            'tinyint': (41, 42, 43, 44, 45, 46, 47, 48, 55, 56, 57, 58, 131, 132, 133, 134, 135),
            'bigint': (67, 68, 69, 70, 79, 80, 81, 82),
            'time': (119, 120, 121, 122, 123, 124),
            'tinyblob': (25, 26),
            'longblob': (31, 32)
            }

    def tearDown(self):
        self.reader.close()
        '''
        with closing(MySQLdb.connect(**self.args)) as conn:
            with closing(conn.cursor()) as cur:
                for cmd in self.sql.split('-- SPLIT')[:2]:
                    cur.execute(cmd)
                conn.commit()
'''
        
    def test_tables(self):
        table_list = list(self.reader.tables)
        assert table_list
        assert len(table_list) == 2

    def test_columns(self):
        for table in self.reader.tables:
            columns = table.columns
            if table.name == 'type_conversion_test_1':
                for k, v in self.type_to_pos.iteritems():
                    assert all(columns[i]['type'] == k for i in v)

            

    def test_indexes(self):
        for table in self.reader.tables:
            assert table.indexes

    def test_constraints(self):
        assert list(self.reader.tables)[1].foreign_keys

