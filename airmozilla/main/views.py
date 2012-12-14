import datetime
import hashlib
import urllib
import vobject

from django import http
from django.conf import settings
from django.contrib.sites.models import RequestSite
from django.shortcuts import get_object_or_404, redirect, render
from django.core.cache import cache
from django.utils.timezone import utc
from django.contrib.syndication.views import Feed

from funfactory.urlresolvers import reverse
from jingo import Template

from airmozilla.main.models import (
    Event, EventOldSlug, Participant, Tag, get_profile_safely
)
from airmozilla.base.utils import (
    paginate, vidly_tokenize, edgecast_tokenize, unhtml,
    VidlyTokenizeError
)
from airmozilla.main.helpers import short_desc


def page(request, template):
    """Base page:  renders templates bare, used for static pages."""
    return render(request, template)


def home(request, page=1):
    """Paginated recent videos and live videos."""
    privacy_filter = {}
    privacy_exclude = {}
    if request.user.is_active:
        profile = get_profile_safely(request.user)
        if profile and profile.contributor:
            privacy_exclude = {'privacy': Event.PRIVACY_COMPANY}
    else:
        privacy_filter = {'privacy': Event.PRIVACY_PUBLIC}

    archived_events = Event.objects.archived()
    if privacy_filter:
        archived_events = archived_events.filter(**privacy_filter)
    elif privacy_exclude:
        archived_events = archived_events.exclude(**privacy_exclude)
    archived_events = archived_events.order_by('-start_time')

    tags = None
    if request.GET.getlist('tag'):
        requested_tags = request.GET.getlist('tag')
        found_tags = []
        not_found_tags = False
        for each in requested_tags:
            try:
                found_tags.append(Tag.objects.get(name__iexact=each).name)
            except Tag.DoesNotExist:
                not_found_tags = True
        if not_found_tags:
            # invalid tags were used in the query string
            url = reverse('main:home')
            if found_tags:
                # some were good
                url += '?%s' % urllib.urlencode({
                    'tag': found_tags
                }, True)
            return redirect(url, permanent=True)
        tags = Tag.objects.filter(name__in=found_tags)
        archived_events = archived_events.filter(tags__in=tags)
    if tags:
        # no live events when filtering by tag
        live_events = Event.objects.none()
    else:

        live_events = (Event.objects.live()
                       .order_by('start_time'))
        if privacy_filter:
            live_events = live_events.filter(**privacy_filter)
        elif privacy_exclude:
            live_events = live_events.exclude(**privacy_exclude)
    archived_paged = paginate(archived_events, page, 10)
    live = None
    also_live = []
    if live_events:
        live, also_live = live_events[0], live_events[1:]
    return render(request, 'main/home.html', {
        'events': archived_paged,
        'live': live,
        'also_live': also_live,
        'tags': tags,
        'Event': Event,
    })


def can_view_event(event, user):
    """return True if the current user has right to view this event"""
    if event.privacy == Event.PRIVACY_PUBLIC:
        return True
    elif not user.is_active:
        return False

    # you're logged in
    if event.privacy == Event.PRIVACY_COMPANY:
        # but then it's not good enough to be contributor
        profile = get_profile_safely(user)
        if profile and profile.contributor:
            return False

    return True


def event(request, slug):
    """Video, description, and other metadata."""
    try:
        event = Event.objects.get(slug=slug)
    except Event.DoesNotExist:
        old_slug = get_object_or_404(EventOldSlug, slug=slug)
        return redirect('main:event', slug=old_slug.event.slug)
    if not can_view_event(event, request.user):
        return redirect('main:login')

    warning = None
    if event.status != Event.STATUS_SCHEDULED:
        if not request.user.is_active:
            return http.HttpResponse('Event not scheduled')
        else:
            warning = "Event is not publicly visible - not scheduled."

    if event.approval_set.filter(approved=False).exists():
        if not request.user.is_active:
            return http.HttpResponse('Event not approved')
        else:
            warning = "Event is not publicly visible - not yet approved."
    template_tagged = ''
    if event.template and not event.is_upcoming():
        context = {
            'md5': lambda s: hashlib.md5(s).hexdigest(),
            'event': event,
            'request': request,
            'datetime': datetime.datetime.utcnow(),
            'vidly_tokenize': vidly_tokenize,
            'edgecast_tokenize': edgecast_tokenize,
        }
        if isinstance(event.template_environment, dict):
            context.update(event.template_environment)
        template = Template(event.template.content)
        try:
            template_tagged = template.render(context)
        except VidlyTokenizeError, msg:
            template_tagged = '<code style="color:red">%s</code>' % msg

    can_edit_event = (
        request.user.is_active and
        request.user.has_perm('main.change_event')
    )

    participants = event.participants.filter(cleared=Participant.CLEARED_YES)
    return render(request, 'main/event.html', {
        'event': event,
        'video': template_tagged,
        'participants': participants,
        'warning': warning,
        'can_edit_event': can_edit_event,
        'Event': Event,
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
    base_qs = Event.objects.approved()
    if public:
        base_qs = base_qs.filter(privacy=Event.PRIVACY_PUBLIC)
    else:
        base_qs = base_qs.exclude(privacy=Event.PRIVACY_PUBLIC)
    events = list(base_qs
                  .filter(start_time__lt=now)
                  .order_by('-start_time')[:settings.CALENDAR_SIZE])
    events += list(base_qs
                   .filter(start_time__gte=now)
                   .order_by('start_time')[:settings.CALENDAR_SIZE])
    base_url = '%s://%s/' % (request.is_secure() and 'https' or 'http',
                             RequestSite(request).domain)
    for event in events:
        vevent = cal.add('vevent')
        vevent.add('summary').value = event.title
        vevent.add('dtstart').value = event.start_time
        vevent.add('dtend').value = (event.start_time +
                                     datetime.timedelta(hours=1))
        vevent.add('description').value = unhtml(short_desc(event))
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


class EventsFeed(Feed):
    title = "AirMozilla"

    description_template = 'main/feeds/event_description.html'

    def get_object(self, request, private_or_public):
        self.private_or_public = private_or_public
        prefix = request.is_secure() and 'https' or 'http'
        self._root_url = '%s://%s' % (prefix, RequestSite(request).domain)

    def link(self):
        return self._root_url + '/'

    def feed_url(self):
        return self.link()

    def items(self):
        now = datetime.datetime.utcnow().replace(tzinfo=utc)

        qs = (
            Event.objects.approved()
            .filter(start_time__lt=now)
            .order_by('-start_time')
        )
        if self.private_or_public == 'private':
            qs = qs.exclude(privacy=Event.PRIVACY_PUBLIC)
        elif self.private_or_public == 'public':
            qs = qs.filter(privacy=Event.PRIVACY_PUBLIC)
        return qs[:settings.FEED_SIZE]

    def item_title(self, event):
        return event.title

    def item_link(self, event):
        return self._root_url + reverse('main:event', args=(event.slug,))

    def item_pubdate(self, event):
        return event.start_time
