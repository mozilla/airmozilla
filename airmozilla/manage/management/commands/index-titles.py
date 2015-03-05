from optparse import make_option

from django.core.management.base import BaseCommand

from airmozilla.manage import autocompeter


class Command(BaseCommand):  # pragma: no cover

    option_list = BaseCommand.option_list + (
        make_option(
            '--max', action='store', dest='max', default=100,
            help='Max number of events to process (default 100)'
        ),
        make_option(
            '--all', action='store_true', dest='all', default=False,
            help='Send in all documents'
        ),
        make_option(
            '--flush-first', action='store_true', dest='flush_first',
            default=False, help='Reset all first'
        ),
    )

    def handle(self, **options):
        verbosity = int(options['verbosity'])
        verbose = verbosity > 1
        max_ = options['max']
        all = options['all']
        flush_first = options['flush_first']
        autocompeter.update(
            verbose=verbose,
            max_=max_,
            all=all,
            flush_first=flush_first,
        )
