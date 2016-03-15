from django.core.management.base import BaseCommand

from airmozilla.manage.videoinfo import fetch_screencaptures


class Command(BaseCommand):  # pragma: no cover

    def add_arguments(self, parser):
        parser.add_argument(
            '--max',
            action='store',
            dest='max',
            default=10,
            help='Max number of events to process (default 10)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            dest='dry_run',
            default=False,
            help='No saving to the database'
        )
        parser.add_argument(
            '-s', '--save-locally',
            action='store_true',
            dest='save_locally',
            default=False,
            help='Save the video file locally (temporary)'
        )
        parser.add_argument(
            '--save-locally-some',
            action='store_true',
            dest='save_locally_some',
            default=False,
            help='Save the video file locally only if public event'
        )
        parser.add_argument(
            '--no-import',
            action='store_true',
            dest='no_import',
            default=False,
            help="Just create the screencaps and don't create Picture instance"
        )

    def handle(self, **options):
        verbosity = int(options['verbosity'])
        import_ = not options['no_import']
        fetch_screencaptures(
            max_=int(options['max']),
            dry_run=options['dry_run'],
            save_locally=options['save_locally'],
            save_locally_some=options['save_locally_some'],
            import_=import_,
            verbose=verbosity > 1
        )
