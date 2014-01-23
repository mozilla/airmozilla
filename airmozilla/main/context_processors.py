import datetime

from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.db.models import Q
from django.utils.timezone import utc

from funfactory.urlresolvers import reverse

from airmozilla.main.models import (
    Event,
    Channel,
    EventHitStats
)
from airmozilla.main.views import is_contributor
from airmozilla.search.forms import SearchForm


def dev(request):
    return {'DEV': settings.DEV, 'DEBUG': settings.DEBUG}


def sidebar(request):
    # none of this is relevant if you're in certain URLs
    if '/manage/' in request.path_info:
        return {}
    data = {
        # used for things like {% if event.attr == Event.ATTR1 %}
        'Event': Event,
    }
    now = datetime.datetime.utcnow().replace(tzinfo=utc)
    yesterday = now - datetime.timedelta(days=1)
    # subtract one second to not accidentally tip it
    yesterday -= datetime.timedelta(seconds=1)
    featured = (
        EventHitStats.objects
        .exclude(event__archive_time__isnull=True)
        .filter(event__archive_time__lt=yesterday)
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

    upcoming = Event.objects.upcoming().order_by('start_time')
    # if viewing a specific page is limited by channel, apply that filtering
    # here too
    if getattr(request, 'channels', None):
        channels = request.channels
    else:
        channels = Channel.objects.filter(slug=settings.DEFAULT_CHANNEL_SLUG)

    feed_privacy = _get_feed_privacy(request.user)

    if settings.DEFAULT_CHANNEL_SLUG in [x.slug for x in channels]:
        feed_title = 'AirMozilla RSS'
        feed_url = reverse('main:feed', args=(feed_privacy,))
        sidebar_channel = settings.DEFAULT_CHANNEL_SLUG
    else:
        _channel = channels[0]
        feed_title = 'AirMozilla - %s - RSS' % _channel.name
        feed_url = reverse('main:channel_feed',
                           args=(_channel.slug, feed_privacy))
        sidebar_channel = _channel.slug
    data['feed_title'] = feed_title
    data['feed_url'] = feed_url

    # `featured` isn't actually a QuerySet on Event
    featured = featured.filter(event__channels__in=channels)
    upcoming = upcoming.filter(channels__in=channels).distinct()

    if not request.user.is_active:
        featured = featured.filter(event__privacy=Event.PRIVACY_PUBLIC)
        upcoming = upcoming.filter(privacy=Event.PRIVACY_PUBLIC)
    upcoming = upcoming[:settings.UPCOMING_SIDEBAR_COUNT]
    data['upcoming'] = upcoming
    data['featured'] = [x.event for x in featured[:5]]

    data['sidebar_top'] = None
    data['sidebar_bottom'] = None
    sidebar_urls_q = (
        Q(url='sidebar_top_%s' % sidebar_channel) |
        Q(url='sidebar_bottom_%s' % sidebar_channel)
    )
    # to avoid having to do 2 queries, make a combined one
    # set it up with an iterator
    for page in FlatPage.objects.filter(sidebar_urls_q):
        if page.url.startswith('sidebar_top_'):
            data['sidebar_top'] = page
        elif page.url.startswith('sidebar_bottom_'):
            data['sidebar_bottom'] = page

    data['search_form'] = SearchForm(request.GET)

    return data


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
