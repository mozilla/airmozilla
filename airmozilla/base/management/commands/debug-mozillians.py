import inspect
from pprint import pprint

from django.core.management.base import BaseCommand, CommandError

from airmozilla.base import mozillians


class Command(BaseCommand):  # pragma: no cover

    args = 'command *args'

    def handle(self, *args, **options):

        try:
            command = args[0]
            command = getattr(mozillians, command)
        except (IndexError, AttributeError):
            functions = (
                mozillians.is_vouched,
                mozillians.fetch_user_name,
                mozillians.in_group,
                mozillians.get_all_groups
            )
            print "Available commands"
            for f in functions:
                print "\t", f.func_name
                print "\t\t", inspect.getargspec(f)
            raise CommandError("No command")
        rest = args[1:]

        result = command(*rest)
        pprint(result)
