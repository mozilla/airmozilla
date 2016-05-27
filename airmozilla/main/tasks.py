from celery import shared_task

from django.conf import settings

from airmozilla.main.models import Chapter, Event
from airmozilla.chapters import images
from airmozilla.base import pictures


@shared_task
def create_chapterimages(chapter_id):
    chapter = Chapter.objects.get(id=chapter_id)
    images.create_chapterimages(
        chapter,
        verbose=settings.DEBUG,
    )


@shared_task
def create_timestamp_pictures(event_id, timestamps):
    event = Event.objects.get(id=event_id)
    assert isinstance(timestamps, list)
    pictures.create_timestamp_pictures(
        event,
        timestamps,
        verbose=settings.DEBUG,
    )


@shared_task
def create_all_timestamp_pictures(event_id):
    event = Event.objects.get(id=event_id)
    pictures.create_all_timestamp_pictures(
        event,
        verbose=settings.DEBUG,
    )
