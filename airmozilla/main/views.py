import datetime
import hashlib
import vobject

from django import http
from django.conf import settings
from django.contrib.sites.models import RequestSite
from django.shortcuts import get_object_or_404, redirect, render
from django.core.cache import cache
from django.http import Http404
from django.utils.timezone import utc

from jingo import Template

from airmozilla.main.models import Event, EventOldSlug, Participant
from airmozilla.base.utils import paginate


def page(request, template):
    """Base page:  renders templates bare, used for static pages."""
    return render(request, template)


def home(request, page=1):
    """Paginated recent videos and live videos."""
    archived_events = Event.objects.archived().order_by('-archive_time')
    live_events = Event.objects.live().order_by('start_time')
    archived_paged = paginate(archived_events, page, 10)
    live = None
    also_live = []
    if live_events:
        live, also_live = live_events[0], live_events[1:]
    return render(request, 'main/home.html', {
        'events': archived_paged,
        'live': live,
        'also_live': also_live
    })


def event(request, slug):
    """Video, description, and other metadata."""
    try:
        event = Event.objects.get(slug=slug)
    except Event.DoesNotExist:
        old_slug = get_object_or_404(EventOldSlug, slug=slug)
        return redirect('main:event', slug=old_slug.event.slug)
    if not event.public and not request.user.is_active:
        return redirect('main:login')
    if event.status != Event.STATUS_SCHEDULED:
        raise Http404('Event not scheduled')
    if event.approval_set.filter(approved=False).exists():
        raise Http404('Event not approved')
    template_tagged = ''
    if event.template and not event.is_upcoming():
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
    participants = event.participants.filter(cleared=Participant.CLEARED_YES)
    return render(request, 'main/event.html', {
        'event': event,
        'video': template_tagged,
        'participants': participants,
    })


def participant(request, slug):
    """Individual participant/speaker profile."""
    participant = get_object_or_404(Participant, slug=slug)
    return render(request, 'main/participant.html', {
        'participant': participant,
    })


def participant_clear(request, clear_token):
    participant = get_object_or_404(Participant, clear_token=clear_token)
    if request.method == 'POST':
        participant.cleared = Participant.CLEARED_YES
        participant.clear_token = ''
        participant.save()
        return render(request, 'main/participant_clear_done.html')
    else:
        return render(request, 'main/participant_clear.html', {
            'participant': participant
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
        if event.location:
            vevent.add('location').value = event.location.name
        vevent.add('url').value = base_url + event.slug + '/'
    icalstream = cal.serialize()
    response = http.HttpResponse(icalstream,
                                 mimetype='text/calendar; charset=utf-8')
    filename = 'AirMozillaEvents%s.ics' % ('Public' if public else 'Private')
    response['Content-Disposition'] = (
        'inline; filename=%s' % filename)
    cache.set(cache_key, response)
    return response
