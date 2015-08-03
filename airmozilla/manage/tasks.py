from celery import shared_task

from django.utils import timezone

from airmozilla.main.models import Event


@shared_task
def sample_updater(event_id):
    """This sample task gets an ID to an Event, then simply just
    updates its `modified` date.
    """
    event = Event.objects.get(id=event_id)
    event.modified = timezone.now()
    event.save()
