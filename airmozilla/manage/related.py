import pyelasticsearch
import datetime

from django.conf import settings
from django.utils import timezone

from airmozilla.main.models import Event

doc_type = 'event'


def get_connection():
    return pyelasticsearch.ElasticSearch(settings.RELATED_CONTENT_URL)


def index(all=False, flush_first=False, since=datetime.timedelta(minutes=10)):
    es = get_connection()

    if flush_first:
        flush(es)

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
            }
        )

    es.refresh(settings.ELASTICSEARCH_PREFIX + settings.ELASTICSEARCH_INDEX)
  # print es.delete_index(settings.ELASTICSEARCH_PREFIX + settings.ELASTICSEARCH_INDEX)

def flush(es=None):
    es = es or get_connection()
    try:
        es.flush(
            settings.ELASTICSEARCH_PREFIX + settings.ELASTICSEARCH_INDEX
        )
    except pyelasticsearch.exceptions.ElasticHttpNotFoundError:
        # if the index isn't there we can't flush it
        pass
    try:
        es.create_index(settings.ELASTICSEARCH_PREFIX + settings.ELASTICSEARCH_INDEX, settings={
            'mappings': {
                doc_type: {
                    'properties': {
                        'privacy': {
                            'type': 'string',
                            'analyzer': 'keyword'
                        },
                        'title': {
                            'type': 'string',
                            # 'index': 'not_analyzed',
                            # supposedly faster for querying but uses more disk space
                            'term_vector': 'yes',
                        },
                        'channels': {
                            'type': 'string',
                            'analyzer': 'keyword'
                        },
                        'tags': {
                            'type': 'string',
                            # 'fields': {
                            #     'raw': {
                            #         'type': 'string',
                            #         'index': 'not_analyzed',
                            #         'term_vector': 'yes',
                            #     }
                            # }
                            'analyzer': 'keyword',
                        }
                    }
                }
            }
        })
    # print es.create_index(index)
    except pyelasticsearch.exceptions.IndexAlreadyExistsError:
        print 'Index already created'
