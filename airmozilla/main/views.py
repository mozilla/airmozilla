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
from django.contrib.flatpages.views import flatpage
from django.views.generic.base import View

from funfactory.urlresolvers import reverse
from jingo import Template

from airmozilla.main.models import (
    Event, EventOldSlug, Participant, Tag, get_profile_safely, Channel,
    Location, EventHitStats
)
from airmozilla.base.utils import (
    paginate,
    edgecast_tokenize,
    unhtml
)
from airmozilla.manage import vidly
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
        if is_contributor(request.user):
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
        # but only do this if it's not filtered by tags
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


def is_contributor(user):
    if not hasattr(user, 'pk'):
        return False
    cache_key = 'is-contributor-%s' % user.pk
    is_ = cache.get(cache_key)
    if is_ is None:
        profile = get_profile_safely(user)
        is_ = False
        if profile and profile.contributor:
            is_ = True
        cache.set(cache_key, is_, 60 * 60)
    return is_


def can_view_event(event, user):
    """return True if the current user has right to view this event"""
    if event.privacy == Event.PRIVACY_PUBLIC:
        return True
    elif not user.is_active:
        return False

    # you're logged in
    if event.privacy == Event.PRIVACY_COMPANY:
        # but then it's not good enough to be contributor
        if is_contributor(user):
            return False

    return True


class EventView(View):
    """Video, description, and other metadata."""

    template_name = 'main/event.html'

    def cant_view_event(self, event, request):
        """return a response appropriate when you can't view the event"""
        return redirect('main:login')

    def cant_find_event(self, request, slug):
        """return an appropriate response if no event can be found"""
        return flatpage(request, slug)

    def can_view_event(self, event, request):
        """wrapper on the utility function can_view_event()"""
        return can_view_event(event, request)

    def get_default_context(self, event, request):
        context = {}
        prefix = request.is_secure() and 'https' or 'http'
        root_url = '%s://%s' % (prefix, RequestSite(request).domain)
        url = reverse('main:event_video', kwargs={'slug': event.slug})
        absolute_url = root_url + url
        context['embed_code'] = (
            '<iframe src="%s" '
            'width="640" height="380" frameborder="0" allowfullscreen>'
            '</iframe>'
            % absolute_url
        )
        return context

    def get(self, request, slug):
        try:
            event = Event.objects.get(slug=slug)
        except Event.DoesNotExist:
            try:
                event = Event.objects.get(slug__iexact=slug)
            except Event.DoesNotExist:
                try:
                    old_slug = EventOldSlug.objects.get(slug=slug)
                    return redirect('main:event', slug=old_slug.event.slug)
                except EventOldSlug.DoesNotExist:
                    # does it exist as a static page
                    return self.cant_find_event(request, slug)

        if not self.can_view_event(event, request.user):
            return self.cant_view_event(event, request)

        warning = None
        if event.status not in (Event.STATUS_SCHEDULED, Event.STATUS_PENDING):
            if not request.user.is_active:
                return http.HttpResponse('Event not scheduled')
            else:
                warning = "Event is not publicly visible - not scheduled."

        if event.approval_set.filter(approved=False).exists():
            if not request.user.is_active:
                return http.HttpResponse('Event not approved')
            else:
                warning = "Event is not publicly visible - not yet approved."

        hits = None

        template_tagged = ''
        if event.template and not event.is_upcoming():
            context = {
                'md5': lambda s: hashlib.md5(s).hexdigest(),
                'event': event,
                'request': request,
                'datetime': datetime.datetime.utcnow(),
                'vidly_tokenize': vidly.tokenize,
                'edgecast_tokenize': edgecast_tokenize,
            }
            if isinstance(event.template_environment, dict):
                context.update(event.template_environment)
            template = Template(event.template.content)
            try:
                template_tagged = template.render(context)
            except vidly.VidlyTokenizeError, msg:
                template_tagged = '<code style="color:red">%s</code>' % msg

            stats_query = (
                EventHitStats.objects.filter(event=event)
                .values_list('total_hits', flat=True)
            )
            for total_hits in stats_query:
                hits = total_hits

        can_edit_event = (
            request.user.is_active and
            request.user.has_perm('main.change_event')
        )

        request.channels = event.channels.all()

        participants = (
            event.participants.filter(cleared=Participant.CLEARED_YES)
        )

        context = self.get_default_context(event, request)
        context.update({
            'event': event,
            'pending': event.status == Event.STATUS_PENDING,
            'video': template_tagged,
            'participants': participants,
            'warning': warning,
            'can_edit_event': can_edit_event,
            'Event': Event,
            'hits': hits,
        })

        return render(request, self.template_name, context)


class EventVideoView(EventView):
    template_name = 'main/event_video.html'

    def can_view_event(self, event, request):
        return event.privacy == Event.PRIVACY_PUBLIC

    def cant_view_event(self, event, request):
        """return a response appropriate when you can't view the event"""
        return render(request, self.template_name, {
            'error': "Not a public event",
            'event': None,
        })

    def cant_find_event(self, request, slug):
        """return an appropriate response if no event can be found"""
        return render(request, self.template_name, {
            'error': "Event not found",
            'event': None
        })

    def get_default_context(self, event, request):
        context = {}
        prefix = request.is_secure() and 'https' or 'http'
        root_url = '%s://%s' % (prefix, RequestSite(request).domain)
        url = reverse('main:event', kwargs={'slug': event.slug})
        context['absolute_url'] = root_url + url
        return context

    def get(self, request, slug):
        response = super(EventVideoView, self).get(request, slug)
        # ALLOWALL is what YouTube uses for sharing
        response['X-Frame-Options'] = 'ALLOWALL'
        return response


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

    def __call__(self, *args, **kwargs):
        response = super(EventsFeed, self).__call__(*args, **kwargs)
        # https://bugzilla.mozilla.org/show_bug.cgi?id=909516
        response['Access-Control-Allow-Origin'] = '*'
        return response


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
