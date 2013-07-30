from django.conf import settings
from django.contrib.flatpages.models import FlatPage
from django.db.models import Q

from funfactory.urlresolvers import reverse

from airmozilla.main.models import (
    Event,
    Channel
)
from airmozilla.main.views import is_contributor


def sidebar(request):
    # none of this is relevant if you're in certain URLs
    if '/manage/' in request.path_info:
        return {}

    data = {
        # used for things like {% if event.attr == Event.ATTR1 %}
        'Event': Event,
    }
    featured = (Event.objects.archived()
                .filter(featured=True).order_by('-start_time'))

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

    featured = featured.filter(channels__in=channels)
    upcoming = upcoming.filter(channels__in=channels)

    if not request.user.is_active:
        featured = featured.filter(privacy=Event.PRIVACY_PUBLIC)
        upcoming = upcoming.filter(privacy=Event.PRIVACY_PUBLIC)
    upcoming = upcoming[:settings.UPCOMING_SIDEBAR_COUNT]
    data['upcoming'] = upcoming
    data['featured'] = featured

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

    return data


def analytics(request):
    # unless specified, the analytics is include if DEBUG = False
    include = getattr(
        settings,
        'INCLUDE_ANALYTICS',
        not settings.DEBUG
    )
    return {'INCLUDE_ANALYTICS': include}


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
