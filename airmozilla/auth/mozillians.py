import logging
import urllib
import json
import requests
from django.conf import settings


class BadStatusCodeError(Exception):
    pass


def is_vouched(email):
    if not getattr(settings, 'MOZILLIANS_API_KEY', None):  # pragma no cover
        logging.warning("'MOZILLIANS_API_KEY' not set up.")
        return False

    # /api/v1/users/?app_name=foobar&app_key=12345&email=test@example.com
    url = settings.MOZILLIANS_API_BASE + '/api/v1/users/'
    data = {
        'app_name': settings.MOZILLIANS_API_APPNAME,
        'app_key': settings.MOZILLIANS_API_KEY,
        'email': email
    }
    url += '?' + urllib.urlencode(data)

    resp = requests.get(url)
    if not resp.status_code == 200:
        url = url.replace(settings.MOZILLIANS_API_KEY, 'xxxscrubbedxxx')
        raise BadStatusCodeError('%s: on: %s' % (resp.status_code, url))
    content = json.loads(resp.content)

    for obj in content['objects']:
        if obj['email'].lower() == email.lower():
            return obj['is_vouched']

    return False
