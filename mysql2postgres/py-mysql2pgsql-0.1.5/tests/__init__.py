import sys
import os
import unittest

sys.path.append(os.path.abspath('../'))

from mysql2pgsql.lib.config import Config
from mysql2pgsql.lib.mysql_reader import MysqlReader
from mysql2pgsql.lib.postgres_writer import PostgresWriter
from mysql2pgsql.lib.errors import ConfigurationFileNotFound

class WithReader(unittest.TestCase):
    def setUp(self):
        try:
            self.config_file = os.path.join(os.path.dirname(__file__), 'mysql2pgsql-test.yml')
            self.config = Config(self.config_file, False)
        except ConfigurationFileNotFound:
            print("In order to run this test you must create the file %s" % config)
            sys.exit(-1)

        self.reader = MysqlReader(self.config.options['mysql'])

    def tearDown(self):
        try:
            self.reader.close()
        except AttributeError:
            pass
