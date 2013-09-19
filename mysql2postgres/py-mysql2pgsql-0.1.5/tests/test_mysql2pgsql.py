import sys
import os
import unittest
import tempfile

sys.path.append(os.path.abspath('../'))

from mysql2pgsql import Mysql2Pgsql
from mysql2pgsql.lib.errors import ConfigurationFileInitialized
class TestFullBoat(unittest.TestCase):
    def setUp(self):
        mock_options = type('MockOptions', (), {'file': os.path.join(os.path.dirname(__file__), 'mysql2pgsql-test.yml'),
                                                 'verbose': False})
        mock_missing_options = type('MockMissingOptions', (), {'file': os.path.join(os.path.dirname(__file__), 'mysql2pgsql-missing.yml'),
                                                 'verbose': False})
        self.options = mock_options()
        self.missing_options = mock_missing_options()

    def test_mysql2pgsql(self):
        m = Mysql2Pgsql(self.options)
        m._get_file = lambda f: tempfile.NamedTemporaryFile()
        m.convert()

        m.file_options['destination']['file'] = None

        m.convert()

    def test_missing_config(self):
        self.assertRaises(ConfigurationFileInitialized, Mysql2Pgsql, self.missing_options)
        
        
    def tearDown(self):
        if os.path.exists(self.missing_options.file):
            os.remove(self.missing_options.file)
