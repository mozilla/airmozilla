import datetime
import hashlib
import vobject

from django import http
from django.conf import settings
from django.contrib.sites.models import RequestSite
from django.core.paginator import Paginator, EmptyPage
from django.shortcuts import get_object_or_404, redirect, render
from django.core.cache import cache
from django.utils.timezone import utc

from jingo import Template

from airmozilla.main.models import Event, EventOldSlug, Participant


def page(request, template):
    """Base page:  renders templates bare, used for static pages."""
    featured = Event.objects.filter(public=True, featured=True)
    return render(request, template, {'featured': featured})


def home(request, page=1):
    """Paginated recent videos and live videos."""
    featured_events = Event.objects.filter(public=True, featured=True)
    archived_events = Event.objects.archived().order_by('-archive_time')
    live_events = Event.objects.live().order_by('start_time')
    upcoming_events = Event.objects.upcoming().order_by('start_time')
    if not request.user.is_active:
        archived_events = archived_events.filter(public=True)
        live_events = live_events.filter(public=True)
        upcoming_events = upcoming_events.filter(public=True)
    upcoming_events = upcoming_events[:3]
    paginate = Paginator(archived_events, 10)
    try:
        archived_paged = paginate.page(page)
    except EmptyPage:
        archived_paged = paginate.page(paginate.num_pages)
    live = None
    also_live = []
    if live_events:
        live, also_live = live_events[0], live_events[1:]
    return render(request, 'main/home.html', {
        'events': archived_paged,
        'featured': featured_events,
        'upcoming': upcoming_events,
        'live': live,
        'also_live': also_live
    })


def event(request, slug):
    """Video, description, and other metadata."""
    featured = Event.objects.filter(public=True, featured=True)
    try:
        event = Event.objects.get(slug=slug)
    except Event.DoesNotExist:
        old_slug = get_object_or_404(EventOldSlug, slug=slug)
        return redirect('main:event', slug=old_slug.event.slug)
    if ((not event.public or event.status == Event.STATUS_INITIATED)
        and not request.user.is_active):
        return redirect('main:login')
    template_tagged = ''
    if event.template:
        context = {
            'md5': lambda s: hashlib.md5(s).hexdigest(),
            'event': event,
            'request': request,
            'datetime': datetime.datetime.utcnow()
        }
        if isinstance(event.template_environment, dict):
            context.update(event.template_environment)
        template = Template(event.template.content)
        template_tagged = template.render(context)
    return render(request, 'main/event.html', {
        'event': event,
        'video': template_tagged,
        'featured': featured,
    })


def participant(request, slug):
    """Individual participant/speaker profile."""
    participant = get_object_or_404(Participant, slug=slug)
    featured = Event.objects.filter(public=True, featured=True)
    if participant.cleared != Participant.CLEARED_YES:
        return redirect('main:login')
    return render(request, 'main/participant.html', {
        'participant': participant,
        'featured': featured
    })


def events_calendar(request, public=True):
    cache_key = 'calendar_%s' % ('public' if public else 'private')
    cached = cache.get(cache_key)
    if cached:
        return cached
    cal = vobject.iCalendar()
    cal.add('X-WR-CALNAME').value = ('Air Mozilla Public Events' if public
                                     else 'Air Mozilla Private Events')
    now = datetime.datetime.utcnow().replace(tzinfo=utc)
    events = list(Event.objects.approved()
                        .filter(start_time__lt=now, public=public) 
                        .order_by('-start_time')[:settings.CALENDAR_SIZE])
    events += list(Event.objects.approved()
                        .filter(start_time__gte=now, public=public)
                        .order_by('start_time')[:settings.CALENDAR_SIZE])
    base_url = '%s://%s/' % (request.is_secure() and 'https' or 'http',
                             RequestSite(request).domain)
    for event in events:
        vevent = cal.add('vevent')
        vevent.add('summary').value = event.title
        vevent.add('dtstart').value = event.start_time
        vevent.add('dtend').value = (event.start_time +
                                     datetime.timedelta(hours=1))
        vevent.add('description').value = event.description
        vevent.add('location').value = event.location
        vevent.add('url').value = base_url + event.slug + '/'
    icalstream = cal.serialize()
    response = http.HttpResponse(icalstream,
                                 mimetype='text/calendar; charset=utf-8')
    filename = 'AirMozillaEvents%s.ics' % ('Public' if public else 'Private')
    response['Content-Disposition'] = (
        'inline; filename=AirmozillaEvents%s.ics' % filename)
    cache.set(cache_key, response)
    return response
