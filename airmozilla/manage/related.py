import pyelasticsearch

from django.conf import settings

from airmozilla.main.models import Event


def indexing():
    es = pyelasticsearch.ElasticSearch(settings.RELATED_CONTENT_URL)

    for event in Event.objects.scheduled_or_processing():
        # should do bulk ops
        es.index(
            'events',
            'event',
            {
                'title': event.title,
                'privacy': event.privacy,
                'tags': [x.name for x in event.tags.all()],
                'channels': [x.name for x in event.channels.all()],
            },
            id=event.id,
        )

    es.refresh()
