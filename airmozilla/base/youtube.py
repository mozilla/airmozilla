import os
import re
import cgi
import urlparse

import requests
from apiclient.discovery import build

from django.core.exceptions import ImproperlyConfigured
from django.conf import settings


YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"


class VideoNotFound(Exception):
    """when the ID leads to nothing"""


class ChannelNotFound(Exception):
    """when the Channel ID leads to nothing"""


def extract_metadata_by_url(url):
    try:
        video_id = cgi.parse_qs(urlparse.urlparse(url).query)['v'][0]
    except KeyError:
        if url.startswith('https://youtu.be/'):
            video_id = url.split('https://youtu.be/')[1].split('/')[0]
            video_id = video_id.split('?')[0]
        else:
            raise ValueError(url)
    return extract_metadata_by_id(video_id)


def extract_metadata_by_id(video_id):
    data = {
        'id': video_id
    }

    if not settings.YOUTUBE_API_KEY:  # pragma: no cover
        raise ImproperlyConfigured('YOUTUBE_API_KEY')

    api = build(
        YOUTUBE_API_SERVICE_NAME,
        YOUTUBE_API_VERSION,
        developerKey=settings.YOUTUBE_API_KEY
    )
    response = api.videos().list(
        id=video_id,
        part='snippet,contentDetails'
    ).execute()
    try:
        item, = response['items']
    except ValueError:
        # either too many too few
        raise VideoNotFound(video_id)

    data['duration'] = youtube_duration_to_seconds(
        item['contentDetails']['duration']
    )
    data['title'] = item['snippet']['title']
    data['description'] = item['snippet']['description']
    data['thumbnail_url'] = find_best_thumbnail_url(
        item['snippet']['thumbnails']
    )
    data['tags'] = item['snippet'].get('tags', [])

    # now we need to find out what channel it was on
    channel_id = item['snippet']['channelId']
    response = api.channels().list(
        id=channel_id,
        part='snippet',
    ).execute()

    try:
        item, = response['items']
    except ValueError:
        # either too many too few
        raise ChannelNotFound(channel_id)
    data['channel'] = {
        'id': item['id'],
        'title': item['snippet']['title'],
        'description': item['snippet']['description'],
        'thumbnail_url': item['snippet']['thumbnails']['high']['url']
    }
    return data


def find_best_thumbnail_url(snippets):
    """return a working URL to a thumbnail that is the biggest possible.

    Because we do our own thumbnail generation from original large
    images we should ideally use the biggest thumbnail possible here.
    """

    biggest = sorted(
        snippets.values(),
        key=lambda x: x['width'],
        reverse=True
    )[0]
    thumbnail_url = biggest['url']
    # Here's the crux, some videos say their highest resolution one is
    # the one called "hqdefault.jpg" but if you just look for it one
    # called "maxresdefault.jpg" it might exist anyway.
    if os.path.basename(thumbnail_url) == 'hqdefault.jpg':
        possible_thumbnail_url = thumbnail_url.replace(
            'hqdefault.jpg',
            'maxresdefault.jpg'
        )
        resp = requests.get(possible_thumbnail_url)
        if resp.status_code == 200:
            thumbnail_url = possible_thumbnail_url
    return thumbnail_url


def youtube_duration_to_seconds(duration):
    seconds = 0
    for number, block in re.findall('(\d+)([HMS])', duration):
        if block == 'H':
            seconds += 60 * 60 * int(number)
        elif block == 'M':
            seconds += 60 * int(number)
        else:
            seconds += int(number)
    return seconds
