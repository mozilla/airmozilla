from urlparse import urlparse

from django.core.management.base import BaseCommand, CommandError

from airmozilla.main.models import Event
from airmozilla.manage.scraper import scrape_urls, get_urls


class Command(BaseCommand):  # pragma: no cover

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
            print scrape_urls(get_urls(event.additional_links))['text']
