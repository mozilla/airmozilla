import datetime

from django.core.paginator import Paginator, EmptyPage
from django.shortcuts import get_object_or_404, redirect, render

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
