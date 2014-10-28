from urlparse import urlparse
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError

from airmozilla.main.models import Event
from airmozilla.manage.videoinfo import fetch_duration


class Command(BaseCommand):  # pragma: no cover

    option_list = BaseCommand.option_list + (
        make_option(
            '--dry-run', action='store_true', dest='dry_run', default=False,
            help='No saving to the database'
        ),
        make_option(
            '-s', '--save-locally', action='store_true', dest='save_locally',
            default=False, help='Save the video file locally (temporary)'
        ),
    )

    args = 'slug-or-url-or-id [slug-or-url-or-id, ...]'

    def handle(self, *args, **options):
        if not args:
            raise CommandError(self.args)
        verbose = int(options['verbosity']) > 1

        for arg in args:
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
