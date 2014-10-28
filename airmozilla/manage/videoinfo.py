import re
import subprocess
import tempfile
import shutil
import os
import time
import sys
import traceback

import requests

from django.conf import settings
from django.template.defaultfilters import filesizeformat

from airmozilla.main.models import Event  # , VidlySubmission
from airmozilla.base.helpers import show_duration
from airmozilla.manage import vidly

REGEX = re.compile('Duration: (\d+):(\d+):(\d+).(\d+)')


def _download_file(url, local_filename):
    # NOTE the stream=True parameter
    r = requests.get(url, stream=True)
    with open(local_filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
                f.flush()


def fetch_duration(event, save=False, save_locally=False, verbose=False):
    assert 'Vid.ly' in event.template.name, "Not a Vid.ly template"
    assert event.template_environment.get('tag'), "No Vid.ly tag in template"

    hd = False
    # This is commented out for the time being because we don't need the
    # HD version to just capture the duration.
    # qs = VidlySubmission.objects.filter(event=event)
    # for submission in qs.order_by('-submission_time')[:1]:
    #     hd = submission.hd

    tag = event.template_environment['tag']
    vidly_url = 'https://vid.ly/%s?content=video&format=' % tag
    if hd:
        vidly_url += 'hd_mp4'
    else:
        vidly_url += 'mp4'

    if event.privacy != Event.PRIVACY_PUBLIC:
        vidly_url += '&token=%s' % vidly.tokenize(tag, 60)

    response = requests.head(vidly_url)
    if response.status_code == 302:
        vidly_url = response.headers['Location']

    response = requests.head(vidly_url)
    assert response.status_code == 200, response.status_code
    if verbose:  # pragma: no cover
        if response.headers['Content-Length']:
            print "Content-Length:",
            print filesizeformat(int(response.headers['Content-Length']))

    if save_locally:
        # store it in a temporary location
        dir_ = tempfile.mkdtemp('videoinfo')
        filepath = os.path.join(dir_, '%s.mp4' % tag)
        t0 = time.time()
        _download_file(vidly_url, filepath)
        t1 = time.time()
        if verbose:  # pragma: no cover
            seconds = int(t1 - t0)
            print "Took", show_duration(seconds, include_seconds=True),
            print "to download"
        vidly_url = filepath

    try:
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
        if verbose:  # pragma: no cover
            print ' '.join(command)
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
    finally:
        if save_locally:
            if os.path.isfile(filepath):
                shutil.rmtree(os.path.dirname(filepath))


def fetch_durations(max_=10, order_by='?', verbose=False, dry_run=False,
                    save_locally=False):
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
            duration = fetch_duration(
                event,
                save=not dry_run,
                save_locally=save_locally,
                verbose=verbose
            )
            if verbose:  # pragma: no cover
                print (
                    "Duration: %s\n" %
                    show_duration(duration, include_seconds=True)
                )
        except AssertionError:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            print ''.join(traceback.format_tb(exc_traceback))
            print exc_type, exc_value
