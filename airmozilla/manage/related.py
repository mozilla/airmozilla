import pyelasticsearch
import datetime

from django.conf import settings
from django.utils import timezone

from airmozilla.main.models import Event
from pyelasticsearch import bulk_chunks

doc_type = 'event'


def get_connection():
    return pyelasticsearch.ElasticSearch(settings.RELATED_CONTENT_URL)


def documents(events, es):
    for event in events:
        yield es.index_op(doc={
            'title': event.title,
            'privacy': event.privacy,
            'tags': [x.name for x in event.tags.all()],
            'channels': [x.name for x in event.channels.all()]
            },
            id=event.id)


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

    # bulk_chunks() breaks our documents into smaller requests for speed:
    for chunk in bulk_chunks(documents(events, es),
                             docs_per_chunk=500,
                             bytes_per_chunk=10000):

        es.bulk(chunk, doc_type='event',
                index=settings.ELASTICSEARCH_PREFIX
                + settings.ELASTICSEARCH_INDEX)

    es.refresh(settings.ELASTICSEARCH_PREFIX + settings.ELASTICSEARCH_INDEX)
#    print es.delete_index(settings.ELASTICSEARCH_PREFIX
#                          + settings.ELASTICSEARCH_INDEX)


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
        es.create_index(settings.ELASTICSEARCH_PREFIX
                        + settings.ELASTICSEARCH_INDEX, settings={
                            'mappings': {
                                doc_type: {
                                    'properties': {
                                        'privacy': {
                                            'type': 'string',
                                            'analyzer': 'keyword'
                                        },
                                        'title': {
                                            'type': 'string',
                                            # supposedly faster for querying
                                            # but uses more disk space
                                            'term_vector': 'yes',
                                        },
                                        'channels': {
                                            'type': 'string',
                                            'analyzer': 'keyword'
                                        },
                                        'tags': {
                                            'type': 'string',
                                            'analyzer': 'keyword',
                                        }
                                    }
                                }
                            }
                        })

    except pyelasticsearch.exceptions.IndexAlreadyExistsError:
        print 'Index already created'


def delete():
    es = get_connection()
    print es.delete_index(settings.ELASTICSEARCH_PREFIX
                          + settings.ELASTICSEARCH_INDEX)
