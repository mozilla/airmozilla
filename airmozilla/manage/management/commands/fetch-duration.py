from urlparse import urlparse

from django.core.management.base import BaseCommand, CommandError

from airmozilla.main.models import Event
from airmozilla.manage.videoinfo import fetch_duration


class Command(BaseCommand):  # pragma: no cover

    def add_arguments(self, parser):
        parser.add_argument('slug-or-url-or-id', nargs='+')

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

    def handle(self, *args, **options):
        identifiers = options['slug-or-url-or-id']

        if not identifiers:
            raise CommandError('slug-or-url-or-id')

        verbose = int(options['verbosity']) > 1

        for arg in identifiers:
            if arg.isdigit():
                event = Event.objects.get(pk=arg)
            else:
                if '://' in arg:
                    slug = urlparse(arg).path.split('/')[1]
                else:
                    slug = arg
                event = Event.objects.get(slug=slug)

            result = fetch_duration(
                event,
                save=not options['dry_run'],
                save_locally=options['save_locally'],
                verbose=verbose,
            )
            if verbose:
                print result
