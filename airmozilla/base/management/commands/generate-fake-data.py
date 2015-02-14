from django.core.management.base import BaseCommand

from airmozilla.base import fakedata


class Command(BaseCommand):  # pragma: no cover

    args = 'number_of_events'

    def handle(self, events=1000, **options):
        events = int(events)
        assert events > 0, events
        verbose = int(options['verbosity']) > 1
        fakedata.generate(events, verbose=verbose)
