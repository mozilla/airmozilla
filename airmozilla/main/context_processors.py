from django.conf import settings

from airmozilla.main.models import Event


def sidebar(request):
    featured = (Event.objects.approved()
                .filter(featured=True).order_by('-start_time'))
    upcoming = Event.objects.upcoming().order_by('start_time')
    if not request.user.is_active:
        featured = featured.filter(privacy=Event.PRIVACY_PUBLIC)
        upcoming = upcoming.filter(privacy=Event.PRIVACY_PUBLIC)
    upcoming = upcoming[:settings.UPCOMING_SIDEBAR_COUNT]
    return {
        'upcoming': upcoming,
        'featured': featured,
        'Event': Event,
    }
