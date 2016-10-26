import os

import requests

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def _get_api_headers():
    if not settings.REV_CLIENT_API_KEY:
        raise ImproperlyConfigured('REV_CLIENT_API_KEY')  # pragma: no cover
    if not settings.REV_USER_API_KEY:
        raise ImproperlyConfigured('REV_USER_API_KEY')  # pragma: no cover
    return {
        'Authorization': 'Rev {}:{}'.format(
            settings.REV_CLIENT_API_KEY,
            settings.REV_USER_API_KEY,
        ),
    }


def get_orders():
    url = settings.REV_BASE_URL + '/api/v1/orders'
    response = requests.get(url, headers=_get_api_headers())
    if response.status_code != 200:
        raise Exception(response.status_code)  # pragma: no cover
    return response.json()


def input_order(video_url, filename=None, content_type=None):
    if not filename:
        filename = os.path.basename(video_url.split('?')[0])
    if not content_type:
        if filename.lower().endswith('.mp4'):
            content_type = 'video/mpeg'
        else:  # pragma: no cover
            raise NotImplementedError(filename)
    url = settings.REV_BASE_URL + '/api/v1/inputs'
    response = requests.post(
        url,
        json={
            'filename': filename,
            'content_type': content_type,
            'url': video_url,
        },
        headers=_get_api_headers(),
    )

    if response.status_code != 201:
        raise Exception(response.status_code)  # pragma: no cover
    return response.headers['Location']


def place_order(uri, output_file_formats=None, webhook_url=None):
    if not output_file_formats:
        output_file_formats = [
            'DFXP',
        ]
    url = settings.REV_BASE_URL + '/api/v1/orders'

    data = {
        'caption_options': {
            'inputs': [
                {
                    'uri': uri,
                }
            ],
            'output_file_formats': output_file_formats
        },
    }
    if webhook_url:
        data['notification'] = {
            'url': webhook_url,
            'level': 'FinalOnly',  # XXX other interesting options?
        }

    response = requests.post(
        url,
        json=data,
        headers=_get_api_headers(),
    )
    if response.status_code != 201:
        raise Exception(response.status_code)  # pragma: no cover
    return response.headers['Location']


def get_order(url):
    response = requests.get(
        url,
        headers=_get_api_headers(),
    )
    if response.status_code != 200:
        raise Exception(response.status_code)  # pragma: no cover
    return response.json()


def cancel_order(order_number):
    url = settings.REV_BASE_URL + '/api/v1/orders/{}/cancel'.format(
        order_number
    )
    response = requests.post(
        url,
        headers=_get_api_headers(),
    )
    if response.status_code != 204:
        raise Exception(response.status_code)  # pragma: no cover
    return True


def get_attachment(id):
    url = settings.REV_BASE_URL + '/api/v1/attachments/{}/content'.format(id)
    response = requests.get(
        url,
        headers=_get_api_headers(),
    )
    if response.status_code != 200:
        raise Exception(response.status_code)  # pragma: no cover
    return response
