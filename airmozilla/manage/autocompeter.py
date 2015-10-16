import datetime
import json
import time
import sys
from pprint import pprint

import requests

from django.conf import settings
from django.utils import timezone
from django.db.models import Count
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse

from airmozilla.main.models import Event, EventHitStats, Approval


def _get_url():
    return getattr(
        settings,
        'AUTOCOMPETER_URL',
        'https://autocompeter.com/v1'
    )


def update(
    verbose=False, all=False, flush_first=False, max_=1000,
    since=datetime.timedelta(minutes=60),
    out=sys.stdout,
):
    if not getattr(settings, 'AUTOCOMPETER_KEY', None):
        if verbose:  # pragma: no cover
            print >>out, "Unable to submit titles to autocompeter.com"
            print >>out, "No settings.AUTOCOMPETER_KEY set up"
        return

    autocompeter_url = _get_url()
    if flush_first:
        assert all, "must be all if you're flushing"
        t0 = time.time()
        response = requests.delete(
            autocompeter_url + '/flush',
            headers={
                'Auth-Key': settings.AUTOCOMPETER_KEY,
            },
            verify=not settings.DEBUG
        )
        t1 = time.time()
        if verbose:  # pragma: no cover
            print >>out, response
            print >>out, "Took", t1 - t0, "seconds to flush"
        assert response.status_code == 204, response.status_code

    now = timezone.now()

    if all:
        hits_map = dict(
            EventHitStats.objects.all().values_list('event', 'total_hits')
        )
        values = hits_map.values()
        if values:
            median_hits = sorted(values)[len(values) / 2]
        else:
            median_hits = 0
        events = Event.objects.scheduled_or_processing()
    else:
        events = (
            Event.objects.scheduled_or_processing()
            .filter(modified__gte=now-since)[:max_]
        )
        if events:
            # there are events, we'll need a hits_map and a median
            hits_map = dict(
                EventHitStats.objects.filter(event__in=events)
                .values_list('event', 'total_hits')
            )
            values = (
                EventHitStats.objects.all()
                .values_list('total_hits', flat=True)
            )
            if values:
                median_hits = sorted(values)[len(values) / 2]
            else:
                median_hits = 0

    title_counts = {}
    # Only bother to set this up if there are events to loop over.
    # Oftentimes the cronjob will trigger here with no new recently changed
    # events and then the loop below ('for event in events:') will do nothing.
    if events:
        grouped_by_title = (
            Event.objects.all().values('title').annotate(Count('title'))
        )
        for each in grouped_by_title:
            title_counts[each['title']] = each['title__count']

    not_approved = Approval.objects.filter(
        event__in=events,
        approved=False,
    ).values_list('event_id', flat=True)

    documents = []
    for event in events:
        url = reverse('main:event', args=(event.slug,))
        title = event.title
        if event.start_time > now:
            # future events can be important too
            popularity = median_hits
        else:
            hits = hits_map.get(event.id, 0)
            popularity = hits
        if event.privacy == Event.PRIVACY_PUBLIC:
            group = ''
            if event.id in not_approved:
                group = Event.PRIVACY_CONTRIBUTORS
        else:
            group = event.privacy

        if title_counts[title] > 1:
            title = '%s %s' % (title, event.start_time.strftime('%d %b %Y'))
        documents.append({
            'title': title,
            'url': url,
            'popularity': popularity,
            'group': group,
        })

    if verbose:  # pragma: no cover
        pprint(documents, stream=out)

    if not documents:
        if verbose:  # pragma: no cover
            print >>out, "No documents."
        return

    t0 = time.time()
    response = requests.post(
        autocompeter_url + '/bulk',
        data=json.dumps({'documents': documents}),
        headers={
            'Auth-Key': settings.AUTOCOMPETER_KEY,
        },
        verify=not settings.DEBUG
    )
    t1 = time.time()
    assert response.status_code == 201, response.status_code
    if verbose:  # pragma: no cover
        print >>out, response
        print >>out, "Took", t1 - t0, "seconds to bulk submit"


def stats():
    if not getattr(settings, 'AUTOCOMPETER_KEY', None):
        raise ImproperlyConfigured("No settings.AUTOCOMPETER_KEY set up")
    autocompeter_url = _get_url()
    response = requests.get(
        autocompeter_url + '/stats',
        headers={
            'Auth-Key': settings.AUTOCOMPETER_KEY,
        },
        verify=not settings.DEBUG
    )
    assert response.status_code == 200, response.status_code
    return response.json()


def test(term, domain=None):
    autocompeter_url = _get_url()
    response = requests.get(
        autocompeter_url,
        params={
            'd': domain or settings.AUTOCOMPETER_DOMAIN,
            'q': term,
        },
        verify=not settings.DEBUG
    )
    assert response.status_code == 200, response.status_code
    return response.json()
