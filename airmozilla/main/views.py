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
from django.template.defaultfilters import slugify

from funfactory.urlresolvers import reverse
from jingo import Template

from airmozilla.main.models import (
    Event, EventOldSlug, Participant, Tag, get_profile_safely, Channel,
    Location
)
from airmozilla.base.utils import (
    paginate, vidly_tokenize, edgecast_tokenize, unhtml,
    VidlyTokenizeError
)
from airmozilla.main.helpers import short_desc


def page(request, template):
    """Base page:  renders templates bare, used for static pages."""
    return render(request, template)


def home(request, page=1, channel_slug=settings.DEFAULT_CHANNEL_SLUG):
    """Paginated recent videos and live videos."""
    channels = Channel.objects.filter(slug=channel_slug)
    if not channels.count():
        if channel_slug == settings.DEFAULT_CHANNEL_SLUG:
            # then, the Main channel hasn't been created yet
            Channel.objects.create(
                name=settings.DEFAULT_CHANNEL_NAME,
                slug=settings.DEFAULT_CHANNEL_SLUG
            )
            channels = Channel.objects.filter(slug=channel_slug)
        else:
            raise http.Http404('Channel not found')

    request.channels = channels

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

    # apply the mandatory channels filter
    live_events = live_events.filter(channels=channels)
    archived_events = archived_events.filter(channels=channels)

    archived_paged = paginate(archived_events, page, 10)
    live = None
    also_live = []
    if live_events:
        live, also_live = live_events[0], live_events[1:]

    # to simplify the complexity of the template when it tries to make the
    # pagination URLs, we just figure it all out here
    next_page_url = prev_page_url = None
    channel = channels[0]
    if archived_paged.has_next():
        if channel.slug == settings.DEFAULT_CHANNEL_SLUG:
            next_page_url = reverse(
                'main:home',
                args=(archived_paged.next_page_number(),)
            )
        else:
            next_page_url = reverse(
                'main:home_channels',
                args=(channel.slug,
                      archived_paged.next_page_number())
            )
    if archived_paged.has_previous():
        if channel.slug == settings.DEFAULT_CHANNEL_SLUG:
            prev_page_url = reverse(
                'main:home',
                args=(archived_paged.previous_page_number(),)
            )
        else:
            prev_page_url = reverse(
                'main:home_channels',
                args=(channel.slug,
                      archived_paged.previous_page_number())
            )

    return render(request, 'main/home.html', {
        'events': archived_paged,
        'live': live,
        'also_live': also_live,
        'tags': tags,
        'Event': Event,
        'channel': channel,
        'next_page_url': next_page_url,
        'prev_page_url': prev_page_url,
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

    request.channels = event.channels.all()

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


def events_calendar(request, privacy=None):
    cache_key = 'calendar'
    if privacy:
        cache_key += '_%s' % privacy
    if request.GET.get('location'):
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
        return cached
    cal = vobject.iCalendar()

    now = datetime.datetime.utcnow().replace(tzinfo=utc)
    base_qs = Event.objects.approved()
    if privacy == 'public':
        base_qs = base_qs.filter(privacy=Event.PRIVACY_PUBLIC)
        title = 'Air Mozilla Public Events'
    elif privacy == 'private':
        base_qs = base_qs.exclude(privacy=Event.PRIVACY_PUBLIC)
        title = 'Air Mozilla Private Events'
    else:
        title = 'Air Mozilla Events'
    if location:
        base_qs = base_qs.filter(location=location)
    cal.add('X-WR-CALNAME').value = title
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
    #response = http.HttpResponse(icalstream,
    #                          mimetype='text/plain; charset=utf-8')

    response = http.HttpResponse(icalstream,
                                 mimetype='text/calendar; charset=utf-8')
    filename = 'AirMozillaEvents%s' % (privacy and privacy or '')
    if location:
        filename += '_%s' % slugify(location.name)
    filename += '.ics'
    response['Content-Disposition'] = (
        'inline; filename=%s' % filename)
    if not location:
        cache.set(cache_key, response)
    return response


class EventsFeed(Feed):
    title = "AirMozilla"

    description_template = 'main/feeds/event_description.html'

    def get_object(self, request, private_or_public='',
                   channel_slug=settings.DEFAULT_CHANNEL_SLUG):
        if private_or_public == 'private':
            # old URL
            private_or_public = 'company'
        self.private_or_public = private_or_public
        prefix = request.is_secure() and 'https' or 'http'
        self._root_url = '%s://%s' % (prefix, RequestSite(request).domain)
        self._channel = get_object_or_404(Channel, slug=channel_slug)

    def link(self):
        return self._root_url + '/'

    def feed_url(self):
        return self.link()

    def items(self):
        now = datetime.datetime.utcnow().replace(tzinfo=utc)

        qs = (
            Event.objects.approved()
            .filter(start_time__lt=now,
                    channels=self._channel)
            .order_by('-start_time')
        )
        if not self.private_or_public or self.private_or_public == 'public':
            qs = qs.filter(privacy=Event.PRIVACY_PUBLIC)
        elif self.private_or_public == 'contributors':
            qs = qs.exclude(privacy=Event.PRIVACY_COMPANY)
        return qs[:settings.FEED_SIZE]

    def item_title(self, event):
        return event.title

    def item_link(self, event):
        return self._root_url + reverse('main:event', args=(event.slug,))

    def item_pubdate(self, event):
        return event.start_time


def channels(request):
    channels = []

    privacy_filter = {}
    privacy_exclude = {}
    if request.user.is_active:
        profile = get_profile_safely(request.user)
        if profile and profile.contributor:
            feed_privacy = 'contributors'
            privacy_exclude = {'privacy': Event.PRIVACY_COMPANY}
        else:
            feed_privacy = 'company'
    else:
        privacy_filter = {'privacy': Event.PRIVACY_PUBLIC}
        feed_privacy = 'public'
    events = Event.objects.archived().all()
    if privacy_filter:
        events = events.filter(**privacy_filter)
    elif privacy_exclude:
        events = events.exclude(**privacy_exclude)

    for channel in Channel.objects.exclude(slug=settings.DEFAULT_CHANNEL_SLUG):
        event_count = events.filter(channels=channel).count()
        channels.append((channel, event_count))
    data = {
        'channels': channels,
        'feed_privacy': feed_privacy,
    }
    return render(request, 'main/channels.html', data)


def calendars(request):
    data = {}
    locations = []
    now = datetime.datetime.utcnow().replace(tzinfo=utc)
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
