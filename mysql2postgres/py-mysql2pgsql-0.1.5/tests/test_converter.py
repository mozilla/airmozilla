from __future__ import with_statement, absolute_import
import os
import sys
import re

from . import WithReader

sys.path.append(os.path.abspath('../'))

from mysql2pgsql.lib.postgres_writer import PostgresWriter
from mysql2pgsql.lib.converter import Converter

class TestConverter(WithReader):
    def setUp(self):
        super(self.__class__, self).setUp()
        mock_writer = type('MockWriter', (PostgresWriter, ), {'close': lambda s: None,
                                                               'write_contents': lambda s, t, r: None})
        self.writer = mock_writer()

    def test_converter(self):
        Converter(self.reader, self.writer, {}, True).convert()
        Converter(self.reader, self.writer, {'force_truncate':True, 'supress_ddl': True}, True).convert()

