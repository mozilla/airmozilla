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
    )

    args = 'slug-or-url-or-id [slug-or-url-or-id, ...]'

    def handle(self, *args, **options):
        if not args:
            raise CommandError(self.args)

        for arg in args:
            if arg.isdigit():
                event = Event.objects.get(pk=arg)
            else:
                if '://' in arg:
                    slug = urlparse(arg).path.split('/')[1]
                else:
                    slug = arg
                event = Event.objects.get(slug=slug)

            print fetch_duration(event, save=not options['dry_run'])
