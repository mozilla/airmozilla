import requests

from django.db.models import Q
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from airmozilla.main.models import Event
from airmozilla.subtitles.models import AmaraVideo
from airmozilla.manage import videoinfo
from airmozilla.main.templatetags.jinja_helpers import thumbnail
from airmozilla.base.utils import build_absolute_url


BASE_URL = 'https://amara.org'


class UploadError(Exception):
    def __init__(self, status_code, error):
        self.status_code = status_code
        self.error = error

    def __str__(self):
        return '{} ({})'.format(self.status_code, self.error)


def _get_headers(**extra):
    if not settings.AMARA_USERNAME:  # pragma: no cover
        raise ImproperlyConfigured('AMARA_USERNAME')
    if not settings.AMARA_API_KEY:  # pragma: no cover
        raise ImproperlyConfigured('AMARA_API_KEY')

    default = {
        'X-api-username': settings.AMARA_USERNAME,
        'X-api-key': settings.AMARA_API_KEY,
    }
    default.update(extra)
    return default


def get_videos():
    return requests.get(
        BASE_URL + '/api/videos/',
        params={
            'team': settings.AMARA_TEAM,
            'project': settings.AMARA_PROJECT,
        },
        headers=_get_headers()
    ).json()


def upload_video(event):
    if isinstance(event, basestring):  # pragma: no cover
        # This is only really used when you use the commandline tool, like
        # ./manage.py debug-amara upload_video my-cool-slug
        if event.isdigit():
            event = Event.objects.get(id=event)
        else:
            event = Event.objects.get(
                Q(slug=event) | Q(title=event)
            )

    video_url = videoinfo.get_video_url(
        event,
        True,
        False,
    )

    # Same dimensions we use for the Open Graph in main/event.html
    picture = event.picture and event.picture.file or event.placeholder_img
    thumb = thumbnail(picture, '385x218', crop='center')

    data = {
        'video_url': video_url,
        'title': event.title,
        'description': event.short_description or event.description,
        'duration': event.duration,
        # 'primary_audio_language_code': event.primary_audio_language_code,
        'team': settings.AMARA_TEAM,
        'project': settings.AMARA_PROJECT,
        'thumbnail': build_absolute_url(thumb.url),
    }

    response = requests.post(
        BASE_URL + '/api/videos/',
        data=data,
        headers=_get_headers()
    )
    if not response.status_code == 201:
        raise UploadError(response.status_code, response.content)

    upload_info = response.json()

    amara_video, _ = AmaraVideo.objects.get_or_create(
        event=event,
        video_url=video_url,
        video_id=upload_info['id'],
        upload_info=upload_info,
    )

    return amara_video
