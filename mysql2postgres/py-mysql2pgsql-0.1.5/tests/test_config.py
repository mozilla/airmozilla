import sys
import os
import unittest
import tempfile

sys.path.append(os.path.abspath('../'))

from mysql2pgsql.lib.config import Config, CONFIG_TEMPLATE
from mysql2pgsql.lib.errors import ConfigurationFileInitialized,\
    ConfigurationFileNotFound

class TestMissingConfig(unittest.TestCase):
    def setUp(self):
        self.temp_file_1 = tempfile.NamedTemporaryFile().name
        temp_file_2 = tempfile.NamedTemporaryFile()
        self.temp_file_2 = temp_file_2.name
        temp_file_2.close()
        
    def test_create_new_file(self):
        self.assertRaises(ConfigurationFileInitialized, Config, self.temp_file_1, True)
        self.assertEqual(CONFIG_TEMPLATE, open(self.temp_file_1).read())

    def test_dont_create_new_file(self):
        self.assertRaises(ConfigurationFileNotFound, Config, self.temp_file_2, False)


class TestDefaultConfig(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.write(CONFIG_TEMPLATE)
        self.temp_file.close()
        
    def tearDown(self):
        os.remove(self.temp_file.name)

    def test_config(self):
        c = Config(self.temp_file.name)
        assert c
        
        options = c.options
        assert options
        self.assertIsInstance(options, dict)
        
        assert 'mysql' in options
        assert 'hostname' in options['mysql']
        assert 'destination' in options
        assert 'file' in options['destination']
        assert 'postgres' in options['destination']
        assert 'supress_data' in options
        assert 'supress_ddl' in options
        assert 'force_truncate' in options
        assert 'only_tables' not in options
        assert 'exclude_tables' not in options
