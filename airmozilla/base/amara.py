import requests

from django.db.models import Q
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from airmozilla.main.models import Event
from airmozilla.subtitles.models import AmaraVideo
from airmozilla.manage import videoinfo
from airmozilla.main.templatetags.jinja_helpers import thumbnail
from airmozilla.base.utils import build_absolute_url


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
        settings.AMARA_BASE_URL + '/api/videos/',
        params={
            'team': settings.AMARA_TEAM,
            'project': settings.AMARA_PROJECT,
        },
        headers=_get_headers()
    ).json()


def get_subtitles(video_id, format='json', language='en'):
    path = '/api/videos/{}/languages/{}/subtitles/'.format(
        video_id,
        language,
    )
    return requests.get(
        settings.AMARA_BASE_URL + path,
        params={
            'format': format,
        },
        headers=_get_headers()
    ).json()


def download_subtitles(video_id):
    amara_video = AmaraVideo.objects.get(video_id=video_id)
    subtitles = get_subtitles(
        amara_video.video_id,
        format='json'
    )
    amara_video.transcript = subtitles
    amara_video.save()


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

    video_url, _ = videoinfo.get_video_url(
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
        settings.AMARA_BASE_URL + '/api/videos/',
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
