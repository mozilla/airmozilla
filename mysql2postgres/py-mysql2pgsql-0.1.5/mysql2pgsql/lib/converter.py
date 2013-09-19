from __future__ import absolute_import

from . import print_start_table


class Converter(object):
    def __init__(self, reader, writer, file_options, verbose=False):
        self.verbose = verbose
        self.reader = reader
        self.writer = writer
        self.file_options = file_options
        self.exclude_tables = file_options.get('exclude_tables', [])
        self.only_tables = file_options.get('only_tables', [])
        self.supress_ddl = file_options.get('supress_ddl', None)
        self.supress_data = file_options.get('supress_data', None)
        self.force_truncate = file_options.get('force_truncate', None)

    def convert(self):
        if self.verbose:
            print_start_table('>>>>>>>>>> STARTING <<<<<<<<<<\n\n')

        tables = [t for t in (t for t in self.reader.tables if t.name not in self.exclude_tables) if not self.only_tables or t.name in self.only_tables]
        if self.only_tables:
            tables.sort(key=lambda t: self.only_tables.index(t.name))
        
        if not self.supress_ddl:
            if self.verbose:
                print_start_table('START CREATING TABLES')

            for table in tables:
                self.writer.write_table(table)

            if self.verbose:
                print_start_table('DONE CREATING TABLES')

        if self.force_truncate and self.supress_ddl:
            if self.verbose:
                print_start_table('START TRUNCATING TABLES')

            for table in tables:
                self.writer.truncate(table)

            if self.verbose:
                print_start_table('DONE TRUNCATING TABLES')

        if not self.supress_data:
            if self.verbose:
                print_start_table('START WRITING TABLE DATA')

            for table in tables:
                self.writer.write_contents(table, self.reader)

            if self.verbose:
                print_start_table('DONE WRITING TABLE DATA')

        if not self.supress_ddl:
            if self.verbose:
                print_start_table('START CREATING INDEXES AND CONSTRAINTS')

            for table in tables:
                self.writer.write_indexes(table)

            for table in tables:
                self.writer.write_constraints(table)

            if self.verbose:
                print_start_table('DONE CREATING INDEXES AND CONSTRAINTS')

        if self.verbose:
            print_start_table('\n\n>>>>>>>>>> FINISHED <<<<<<<<<<')

        self.writer.close()
