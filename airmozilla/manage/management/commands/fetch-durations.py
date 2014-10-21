from optparse import make_option

from django.core.management.base import BaseCommand

from airmozilla.manage.videoinfo import fetch_durations


class Command(BaseCommand):  # pragma: no cover

    option_list = BaseCommand.option_list + (
        make_option(
            '--max', action='store', dest='max', default=10,
            help='Max number of events to process (default 10)'
        ),
        make_option(
            '--dry-run', action='store_true', dest='dry_run', default=False,
            help='No saving to the database'
        ),
    )

    def handle(self, **options):
        verbosity = int(options['verbosity'])
        fetch_durations(
            max_=int(options['max']),
            dry_run=options['dry_run'],
            verbose=verbosity > 1
        )
