import datetime

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import utc

from airmozilla.main.models import Event, EventOldSlug, Participant


def page(request, template):
    """Base page:  renders templates bare, used for static pages."""
    featured = Event.objects.filter(public=True, featured=True)
    return render(request, template, {'featured': featured})


def home(request, page=1):
    """Paginated recent videos and live videos."""
    featured = Event.objects.filter(public=True, featured=True)
    now = datetime.datetime.utcnow().replace(tzinfo=utc)
    past_filter = {'end_time__lt': now, 'status': Event.STATUS_SCHEDULED}
    live_filter = {'end_time__gt': now, 'start_time__lt': now,
                   'status': Event.STATUS_SCHEDULED}
    if not request.user.is_active:
        past_filter['public'] = True
        live_filter['public'] = True
    past_events = Event.objects.filter(**past_filter).order_by('-end_time')
    live_events = Event.objects.filter(**live_filter).order_by('-end_time')
    paginate = Paginator(past_events, 10)
    try:
        past_events_paged = paginate.page(page)
    except PageNotAnInteger:
        past_events_paged = paginate.page(1)
    except EmptyPage:
        past_events_paged = paginate.page(paginate.num_pages)
    live = False
    also_live = []
    if live_events:
        live = live_events[0]
        also_live = live_events[1:]
    return render(request, 'main/home.html', {
        'events': past_events_paged,
        'featured': featured,
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
    return render(request, 'main/event.html', {
        'event': event,
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
