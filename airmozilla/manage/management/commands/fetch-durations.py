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
        make_option(
            '-s', '--save-locally', action='store_true', dest='save_locally',
            default=False, help='Save the video file locally (temporary)'
        ),
        make_option(
            '--save-locally-some', action='store_true',
            dest='save_locally_some',
            default=False,
            help='Save the video file locally only if public event'
        ),
    )

    def handle(self, **options):
        verbosity = int(options['verbosity'])
        fetch_durations(
            max_=int(options['max']),
            dry_run=options['dry_run'],
            save_locally=options['save_locally'],
            save_locally_some=options['save_locally_some'],
            verbose=verbosity > 1
        )
