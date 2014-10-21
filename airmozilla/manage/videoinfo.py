import re
import subprocess

import requests

from django.conf import settings
# from django.core.cache import cache

from airmozilla.main.models import VidlySubmission, Event
from airmozilla.base.helpers import show_duration
from airmozilla.manage import vidly

REGEX = re.compile('Duration: (\d+):(\d+):(\d+).(\d+)')


def fetch_duration(event, save=False):
    assert 'Vid.ly' in event.template.name, "Not a Vid.ly template"
    assert event.template_environment.get('tag'), "No Vid.ly tag in template"

    hd = False
    qs = VidlySubmission.objects.filter(event=event)
    for submission in qs.order_by('-submission_time')[:1]:
        hd = submission.hd

    tag = event.template_environment['tag']
    vidly_url = 'https://vid.ly/%s?content=video&format=' % tag
    if hd:
        vidly_url += 'hd_mp4'
    else:
        vidly_url += 'mp4'

    if event.privacy != Event.PRIVACY_PUBLIC:
        vidly_url += '&token=%s' % vidly.tokenize(tag, 60)

    response = requests.head(vidly_url)
    assert response.status_code in (200, 302), response.status_code

    ffmpeg_location = getattr(
        settings,
        'FFMPEG_LOCATION',
        'ffmpeg'
    )
    command = [
        ffmpeg_location,
        '-i',
        vidly_url,
    ]
    # print ' '.join(command)
    out, err = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    ).communicate()

    matches = REGEX.findall(err)
    if matches:
        found, = matches
        hours = int(found[0])
        minutes = int(found[1])
        minutes += hours * 60
        seconds = int(found[2])
        seconds += minutes * 60
        if save:
            event.duration = seconds
            event.save()
        return seconds


def fetch_durations(max_=10, order_by='?', verbose=False, dry_run=False):
    """this can be called by a cron job that will try to fetch
    duration for as many events as it can."""
    qs = (
        Event.objects
        .filter(duration__isnull=True)
        .filter(template__name__icontains='Vid.ly')
    )

    for event in qs.order_by('?')[:max_]:
        if verbose:  # pragma: no cover
            print "Event: %r, (privacy:%s slug:%s)" % (
                event.title,
                event.get_privacy_display(),
                event.slug,
            )

        if not event.template_environment.get('tag'):
            if verbose:  # pragma: no cover
                print "No Vid.ly Tag!"
            continue

        try:
            duration = fetch_duration(event, save=not dry_run)
            if verbose:  # pragma: no cover
                print (
                    "Duration: %s\n" %
                    show_duration(duration, include_seconds=True)
                )
        except AssertionError as exp:  # pragma: no cover
            if verbose:
                print "AssertionError!"
                print exp
