import datetime

import pyelasticsearch

from django.conf import settings
from django.utils import timezone
from django.contrib.sites.models import Site
from django.core.cache import cache

from airmozilla.main.models import Event
from airmozilla.base.utils import STOPWORDS


doc_type = 'event'


def get_connection():
    return pyelasticsearch.ElasticSearch(settings.ELASTICSEARCH_URL)


def get_index():
    cache_key = 'related_index'
    value = cache.get(cache_key)
    if value is None:
        value = Site.objects.get_current().domain
        value += settings.ELASTICSEARCH_PREFIX + settings.ELASTICSEARCH_INDEX
        cache.set(cache_key, value, 60 * 60)  # this could probably be longer
    return value


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
        create(es)

    if all:
        events = Event.objects.scheduled_or_processing()
    else:
        now = timezone.now()
        events = (
            Event.objects.scheduled_or_processing()
            .filter(modified__gte=now-since)
        )

    # bulk_chunks() breaks our documents into smaller requests for speed
    index = get_index()
    for chunk in pyelasticsearch.bulk_chunks(
        documents(events, es),
        docs_per_chunk=500,
        bytes_per_chunk=10000
    ):
        es.bulk(chunk, doc_type=doc_type, index=index)

    es.refresh(index)


def flush(es=None):
    es = es or get_connection()
    index = get_index()
    try:
        es.flush(index)
    except pyelasticsearch.exceptions.ElasticHttpNotFoundError:
        # if the index isn't there we can't flush it
        pass


def create(es=None):
    es = es or get_connection()
    index = get_index()
    try:
        es.create_index(index, settings={
            'settings': {
                'analysis': {
                    'analyzer': {
                        'extended_snowball_analyzer': {
                            'type': 'snowball',
                            'stopwords': STOPWORDS,
                        },
                    },
                },
            },
            'mappings': {
                doc_type: {
                    'properties': {
                        'privacy': {
                            'type': 'string',
                            'analyzer': 'keyword'
                        },
                        'title': {
                            'type': 'string',
                            'analyzer': 'extended_snowball_analyzer',
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
        pass  # Index already created


def delete(es=None):
    es = es or get_connection()
    es.delete_index(get_index())
