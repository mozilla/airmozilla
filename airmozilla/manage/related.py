import pyelasticsearch
import datetime

from django.conf import settings
from django.utils import timezone

from airmozilla.main.models import Event


def index(all=False, flush_first=False, since=datetime.timedelta(minutes=10)):
    es = pyelasticsearch.ElasticSearch(settings.RELATED_CONTENT_URL)

    if flush_first:
        es.flush(settings.ELASTICSEARCH_PREFIX + settings.ELASTICSEARCH_INDEX)

    if all:
        events = Event.objects.scheduled_or_processing()
    else:
        now = timezone.now()
        events = Event.objects.scheduled_or_processing() \
            .filter(modified__gte=now-since)

    for event in events:
        # should do bulk ops
        es.index(
            settings.ELASTICSEARCH_PREFIX + settings.ELASTICSEARCH_INDEX,
            'event',
            {
                'title': event.title,
                'privacy': event.privacy,
                'tags': [x.name for x in event.tags.all()],
                'channels': [x.name for x in event.channels.all()],
            },
            id=event.id,

        )

    es.refresh(settings.ELASTICSEARCH_PREFIX + settings.ELASTICSEARCH_INDEX)
