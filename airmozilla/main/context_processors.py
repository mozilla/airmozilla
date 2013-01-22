from django.conf import settings
from funfactory.urlresolvers import reverse

from airmozilla.main.models import Event, Channel


def sidebar(request):
    # none of this is relevant if you're in certain URLs
    if '/manage/' in request.path_info:
        return {}

    data = {
        'Event': Event,
    }
    featured = (Event.objects.approved()
                .filter(featured=True).order_by('-start_time'))
    upcoming = Event.objects.upcoming().order_by('start_time')
    # if viewing a specific page is limited by channel, apply that filtering
    # here too
    if getattr(request, 'channels', None):
        channels = request.channels
    else:
        channels = Channel.objects.filter(slug=settings.DEFAULT_CHANNEL_SLUG)
    if settings.DEFAULT_CHANNEL_SLUG in [x.slug for x in channels]:
        feed_title = 'AirMozilla RSS'
        feed_url = reverse('main:feed')
    else:
        _channel = channels[0]
        feed_title = 'AirMozilla - %s - RSS' % _channel.name
        feed_url = reverse('main:channel_feed', args=(_channel.slug, 'public'))
    data['feed_title'] = feed_title
    data['feed_url'] = feed_url

    featured = featured.filter(channels=channels)
    upcoming = upcoming.filter(channels=channels)

    if not request.user.is_active:
        featured = featured.filter(privacy=Event.PRIVACY_PUBLIC)
        upcoming = upcoming.filter(privacy=Event.PRIVACY_PUBLIC)
    upcoming = upcoming[:settings.UPCOMING_SIDEBAR_COUNT]
    data['upcoming'] = upcoming
    data['featured'] = featured

    return data
