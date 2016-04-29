import inspect
from pprint import pprint

from django.core.management.base import BaseCommand, CommandError

from airmozilla.base import amara


class Command(BaseCommand):  # pragma: no cover

    args = 'command *args'

    def handle(self, *args, **options):
        try:
            command = args[0]
            command = getattr(amara, command)
        except (IndexError, AttributeError):
            print "Available commands"
            for name, member in inspect.getmembers(amara):
                if inspect.isfunction(member):
                    if name.startswith('_'):
                        continue
                    print "\t", name
                    print "\t\t", inspect.getargspec(member)

            raise CommandError("No command")
        rest = args[1:]

        result = command(*rest)
        pprint(result)
