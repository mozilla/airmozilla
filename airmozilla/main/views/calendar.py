import datetime

import vobject

from django import http
from django.shortcuts import get_object_or_404, render
from django.utils.timezone import utc
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from django.db.models import Q
from django.core.urlresolvers import reverse

from slugify import slugify
from jsonview.decorators import json_view

from airmozilla.base.utils import get_base_url
from airmozilla.main.templatetags.jinja_helpers import short_desc
from airmozilla.main.models import (
    Event,
    get_profile_safely,
    Location,
    Channel,
)
from airmozilla.search.models import SavedSearch
from airmozilla.main.views import is_contributor
from airmozilla.main import forms


def calendar(request):
    context = {}
    return render(request, 'main/calendar.html', context)


@json_view
def calendar_data(request):
    form = forms.CalendarDataForm(request.GET)
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    start = form.cleaned_data['start']
    end = form.cleaned_data['end']

    start = start.replace(tzinfo=utc)
    end = end.replace(tzinfo=utc)

    privacy_filter = {}
    privacy_exclude = {}
    events = Event.objects.scheduled_or_processing()
    if request.user.is_active:
        if is_contributor(request.user):
            privacy_exclude = {'privacy': Event.PRIVACY_COMPANY}
    else:
        privacy_filter = {'privacy': Event.PRIVACY_PUBLIC}
        events = events.approved()

    if privacy_filter:
        events = events.filter(**privacy_filter)
    elif privacy_exclude:
        events = events.exclude(**privacy_exclude)

    events = events.filter(
        start_time__gte=start,
        start_time__lt=end
    )
    event_objects = []
    for event in events.select_related('location'):
        start_time = event.start_time
        end_time = start_time + datetime.timedelta(
            seconds=max(event.duration or event.estimated_duration, 60 * 20)
        )
        # We don't need 'end' because we don't yet know how long the event
        # was or will be.
        event_objects.append({
            'title': event.title,
            'start': start_time.isoformat(),
            'end': end_time.isoformat(),
            'url': reverse('main:event', args=(event.slug,)),
            'description': short_desc(event),
            'allDay': False,
        })

    return event_objects


def calendars(request):
    data = {}
    locations = []
    now = timezone.now()
    time_ago = now - datetime.timedelta(days=30)
    base_qs = Event.objects.filter(start_time__gte=time_ago)
    for location in Location.objects.all().order_by('name'):
        count = base_qs.filter(location=location).count()
        if count:
            locations.append(location)
    data['locations'] = locations
    if request.user.is_active:
        profile = get_profile_safely(request.user)
        if profile and profile.contributor:
            data['calendar_privacy'] = 'contributors'
        else:
            data['calendar_privacy'] = 'company'
    else:
        data['calendar_privacy'] = 'public'
    return render(request, 'main/calendars.html', data)


def events_calendar_ical(request, privacy=None, channel_slug=None):
    cache_key = 'calendar'
    savedsearch = None
    if privacy:
        cache_key += '_%s' % privacy
    if channel_slug:
        cache_key += '_%s' % channel_slug
    if request.GET.get('ss'):
        savedsearch = get_object_or_404(SavedSearch, id=request.GET['ss'])
        cache_key += '_%s' % savedsearch.pk
    if request.GET.get('location'):
        if request.GET.get('location').isdigit():
            location = get_object_or_404(
                Location,
                pk=request.GET.get('location')
            )
        else:
            location = get_object_or_404(
                Location,
                name=request.GET.get('location')
            )
        cache_key += str(location.pk)
        cached = None
    else:
        location = None
        cached = cache.get(cache_key)

    if cached:
        # additional response headers aren't remembered so add them again
        cached['Access-Control-Allow-Origin'] = '*'
        return cached
    cal = vobject.iCalendar()

    now = timezone.now()
    if savedsearch:
        base_qs = savedsearch.get_events()
    else:
        base_qs = Event.objects.scheduled_or_processing()
    if channel_slug:
        channel = get_object_or_404(
            Channel,
            slug__iexact=channel_slug
        )
        channels = Channel.objects.filter(
            Q(id=channel.id) |
            Q(parent=channel.id)
        )
        base_qs = base_qs.filter(channels__in=channels)

    if privacy == 'public':
        base_qs = base_qs.approved().filter(
            privacy=Event.PRIVACY_PUBLIC
        )
        title = 'Air Mozilla Public Events'
    elif privacy == 'private':
        base_qs = base_qs.exclude(
            privacy=Event.PRIVACY_PUBLIC
        )
        title = 'Air Mozilla Private Events'
    else:
        title = 'Air Mozilla Events'
    if savedsearch:
        if savedsearch.name:
            title += ' (from saved search "{}")'.format(savedsearch.name)
        else:
            title += ' (from saved search)'
    if location:
        base_qs = base_qs.filter(location=location)

    cal.add('X-WR-CALNAME').value = title
    events = list(base_qs
                  .filter(start_time__lt=now)
                  .order_by('-start_time')[:settings.CALENDAR_SIZE])
    events += list(base_qs
                   .filter(start_time__gte=now)
                   .order_by('start_time'))
    base_url = get_base_url(request)
    for event in events:
        vevent = cal.add('vevent')
        vevent.add('summary').value = event.title
        vevent.add('dtstart').value = event.start_time
        vevent.add('dtend').value = (
            event.start_time +
            datetime.timedelta(
                seconds=event.duration or event.estimated_duration
            )
        )
        vevent.add('description').value = short_desc(event, strip_html=True)
        if event.location:
            vevent.add('location').value = event.location.name
        vevent.add('url').value = (
            base_url + reverse('main:event', args=(event.slug,))
        )
    icalstream = cal.serialize()
    # response = http.HttpResponse(
    #     icalstream,
    #     content_type='text/plain; charset=utf-8'
    # )
    response = http.HttpResponse(
        icalstream,
        content_type='text/calendar; charset=utf-8'
    )
    filename = 'AirMozillaEvents%s' % (privacy and privacy or '')
    if location:
        filename += '_%s' % slugify(location.name)
    if savedsearch:
        filename += '_ss%s' % savedsearch.id
    filename += '.ics'
    response['Content-Disposition'] = (
        'inline; filename=%s' % filename)
    if not location:
        cache.set(cache_key, response, 60 * 10)  # 10 minutes

    # https://bugzilla.mozilla.org/show_bug.cgi?id=909516
    response['Access-Control-Allow-Origin'] = '*'

    return response
