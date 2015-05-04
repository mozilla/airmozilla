import datetime

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from django.core.cache import cache

from funfactory.urlresolvers import reverse

from airmozilla.main.models import (
    Event,
    Channel,
    EventHitStats,
    most_recent_event
)
from airmozilla.main.views import is_contributor
from airmozilla.search.forms import SearchForm
from airmozilla.staticpages.models import StaticPage


def dev(request):
    return {'DEV': settings.DEV, 'DEBUG': settings.DEBUG}


def sidebar(request):
    # none of this is relevant if you're in certain URLs

    if '/manage/' in request.path_info:
        return {}
    if '/roku/' in request.path_info:
        # Special circumstance here.
        # We have a static page with URL "/roku" (which django redirects
        # to "/roku/"). On that page we want sidebar stuff.
        # But on all XML related roku views we don't want sidebar stuff.
        if not request.path_info.endswith('/roku/'):
            return {}

    data = {
        # used for things like {% if event.attr == Event.ATTR1 %}
        'Event': Event,
    }

    # if viewing a specific page is limited by channel, apply that filtering
    # here too
    if getattr(request, 'channels', None):
        channels = request.channels
    else:
        channels = Channel.objects.filter(slug=settings.DEFAULT_CHANNEL_SLUG)

    feed_privacy = _get_feed_privacy(request.user)

    if settings.DEFAULT_CHANNEL_SLUG in [x.slug for x in channels]:
        feed_title = 'Air Mozilla RSS'
        feed_url = reverse('main:feed', args=(feed_privacy,))
        sidebar_channel = settings.DEFAULT_CHANNEL_SLUG
    else:
        _channel = channels[0]
        feed_title = 'Air Mozilla - %s - RSS' % _channel.name
        feed_url = reverse('main:channel_feed',
                           args=(_channel.slug, feed_privacy))
        sidebar_channel = _channel.slug
    data['feed_title'] = feed_title
    data['feed_url'] = feed_url

    data['upcoming'] = get_upcoming_events(channels, request.user)
    data['featured'] = get_featured_events(channels, request.user)

    data['sidebar_top'] = None
    data['sidebar_bottom'] = None
    sidebar_urls_q = (
        Q(url='sidebar_top_%s' % sidebar_channel) |
        Q(url='sidebar_bottom_%s' % sidebar_channel) |
        Q(url='sidebar_top_*') |
        Q(url='sidebar_bottom_*')
    )
    # to avoid having to do 2 queries, make a combined one
    # set it up with an iterator
    for page in StaticPage.objects.filter(sidebar_urls_q):
        if page.url.startswith('sidebar_top_'):
            data['sidebar_top'] = page
        elif page.url.startswith('sidebar_bottom_'):
            data['sidebar_bottom'] = page

    data['search_form'] = SearchForm(request.GET)

    return data


def get_upcoming_events(channels, user,
                        length=settings.UPCOMING_SIDEBAR_COUNT):
    """return a queryset of upcoming events"""
    anonymous = True
    contributor = False
    if user.is_active:
        anonymous = False
        if is_contributor(user):
            contributor = True

    cache_key = 'upcoming_events_%s_%s' % (int(anonymous), int(contributor))
    cache_key += ','.join(str(x.id) for x in channels)
    event = most_recent_event()
    if event:
        cache_key += str(event.modified.microsecond)
    upcoming = cache.get(cache_key)
    if upcoming is None:
        upcoming = _get_upcoming_events(channels, anonymous, contributor)
        upcoming = upcoming[:length]
        cache.set(cache_key, upcoming, 60 * 60)
    return upcoming


def _get_upcoming_events(channels, anonymous, contributor):
    """do the heavy lifting of getting the featured events"""
    upcoming = Event.objects.upcoming().order_by('start_time')
    upcoming = upcoming.filter(channels__in=channels).distinct()
    upcoming = upcoming.select_related('picture')

    if anonymous:
        upcoming = upcoming.exclude(privacy=Event.PRIVACY_COMPANY)
    elif contributor:
        upcoming = upcoming.filter(privacy=Event.PRIVACY_PUBLIC)
    return upcoming


def get_featured_events(
    channels,
    user,
    length=settings.FEATURED_SIDEBAR_COUNT
):
    """return a list of events that are sorted by their score"""
    anonymous = True
    contributor = False
    if user.is_active:
        anonymous = False
        if is_contributor(user):
            contributor = True

    cache_key = 'featured_events_%s_%s' % (int(anonymous), int(contributor))
    if channels:
        cache_key += ','.join(str(x.id) for x in channels)
    event = most_recent_event()
    if event:
        cache_key += str(event.modified.microsecond)
    featured = cache.get(cache_key)
    if featured is None:
        featured = _get_featured_events(channels, anonymous, contributor)
        featured = featured[:length]
        cache.set(cache_key, featured, 60 * 60)
    return [x.event for x in featured]


def _get_featured_events(channels, anonymous, contributor):
    """do the heavy lifting of getting the featured events"""
    now = timezone.now()
    yesterday = now - datetime.timedelta(days=1)
    # subtract one second to not accidentally tip it
    yesterday -= datetime.timedelta(seconds=1)
    featured = (
        EventHitStats.objects
        .exclude(event__archive_time__isnull=True)
        .filter(event__archive_time__lt=yesterday)

        .exclude(event__channels__exclude_from_trending=True)
        .extra(
            select={
                # being 'featured' pretends the event has twice as
                # many hits as actually does
                'score': '(featured::int + 1) * total_hits'
                         '/ extract(days from (now() - archive_time)) ^ 1.8',
            }
        )
        .select_related('event')
        .order_by('-score')
    )
    if channels:
        featured = featured.filter(event__channels__in=channels)

    if anonymous:
        featured = featured.filter(event__privacy=Event.PRIVACY_PUBLIC)
    elif contributor:
        featured = featured.exclude(event__privacy=Event.PRIVACY_COMPANY)
    featured = featured.select_related('event__picture')
    return featured


def analytics(request):
    # unless specified, the analytics is include if DEBUG = False
    if request.path_info.startswith('/manage/'):
        include = False
    else:
        include = getattr(
            settings,
            'INCLUDE_ANALYTICS',
            not settings.DEBUG
        )
    return {'include_analytics': include}


def _get_feed_privacy(user):
    """return 'public', 'contributors' or 'company' depending on the user
    profile.
    Because this is used very frequently and because it's expensive to
    pull out the entire user profile every time, we use cache to remember
    if the user is a contributor or not (applicable only if logged in)
    """
    if user.is_active:
        if is_contributor(user):
            return 'contributors'
        return 'company'
    return 'public'


def browserid(request):
    # by making this a function, it means we only need to run this
    # when ``redirect_next()`` is called
    def redirect_next():
        next = request.GET.get('next')
        if next:
            if '://' in next:
                return reverse('main:home')
            return next
        url = request.META['PATH_INFO']
        if url in (reverse('main:login'), reverse('main:login_failure')):
            # can't have that!
            url = reverse('main:home')
        return url
    return {'redirect_next': redirect_next}


def faux_i18n(request):
    """We don't do I18N but we also don't want to necessarily delete
    all the hard work on using `_('English')` in templates because
    maybe one day we'll start doing I18N and then it might be good
    to keep these annotations in the templates."""
    def _(*args, **kwargs):
        return args[0]

    return {'_': _}


def autocompeter(request):
    """We need to tell the Autocompeter service which groups the current
    user should be able to view."""
    key = getattr(settings, 'AUTOCOMPETER_KEY', None)
    if not key:
        return {}

    groups = []
    if request.user and request.user.is_active:
        groups.append(Event.PRIVACY_CONTRIBUTORS)
        if not is_contributor(request.user):
            groups.append(Event.PRIVACY_COMPANY)
    url = getattr(settings, 'AUTOCOMPETER_URL', '')
    domain = getattr(settings, 'AUTOCOMPETER_DOMAIN', '')
    enabled = getattr(settings, 'AUTOCOMPETER_ENABLED', True)
    return {
        'include_autocompeter': enabled,
        'autocompeter_domain': domain,
        'autocompeter_groups': ','.join(groups),
        'autocompeter_url': url,
    }
