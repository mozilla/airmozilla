from django.core.management.base import NoArgsCommand
from airmozilla.manage.archiver import archive
from airmozilla.main.models import Event


class Command(NoArgsCommand):  # pragma: no cover

    def handle(self, **options):
        events = (
            Event.objects
            .filter(status=Event.STATUS_PENDING,
                    archive_time__isnull=True,
                    template__name__contains='Vid.ly')
        )
        for event in events:
            archive(event)
