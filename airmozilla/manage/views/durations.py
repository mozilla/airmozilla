from django.shortcuts import render

from airmozilla.manage import vidly
from airmozilla.main.models import Event
from .decorators import superuser_required


@superuser_required
def report_all(request):
    events = (
        Event.objects.archived()
        .filter(template__name__icontains='vid.ly')
        .filter(template_environment__icontains='tag')
        .order_by('-start_time')
    )[:1000]  # Vid.ly's GetMediaList is capped at 1000 most recent submissions

    vidly_durations = {}
    for tag, information in vidly.medialist('Finished').items():
        try:
            vidly_durations[tag] = float(information['Duration'])
        except KeyError:
            pass

    def equalish_duration(duration1, duration2):
        return abs(duration1 - duration2) <= 1

    context = {
        'events': events,
        'vidly_durations': vidly_durations,
        'equalish_duration': equalish_duration,
    }
    return render(request, 'manage/durations.html', context)
