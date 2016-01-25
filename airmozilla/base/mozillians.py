import logging
import urllib
import json

import requests

from django.core.cache import cache
from django.conf import settings


class BadStatusCodeError(Exception):
    pass


def _fetch_users(email=None, group=None, is_username=False, **options):
    if not getattr(settings, 'MOZILLIANS_API_KEY', None):  # pragma no cover
        logging.warning("'MOZILLIANS_API_KEY' not set up.")
        return False

    url = settings.MOZILLIANS_API_BASE + '/api/v2/users/'
    options['api-key'] = settings.MOZILLIANS_API_KEY
    if email:
        if is_username:
            options['username'] = email
        else:
            options['email'] = email
    if group:
        if isinstance(group, (list, tuple)):  # pragma: no cover
            raise NotImplementedError(
                'You can not find users by MULTIPLE groups'
            )
        options['group'] = group
    url += '?' + urllib.urlencode(options)

    resp = requests.get(url)
    if resp.status_code != 200:
        url = url.replace(settings.MOZILLIANS_API_KEY, 'xxxscrubbedxxx')
        raise BadStatusCodeError('%s: on: %s' % (resp.status_code, url))
    return json.loads(resp.content)


def _fetch_user(url):
    options = {}
    assert 'api-key=' not in url, url
    options['api-key'] = settings.MOZILLIANS_API_KEY
    url += '?' + urllib.urlencode(options)
    resp = requests.get(url)
    if resp.status_code != 200:
        url = url.replace(settings.MOZILLIANS_API_KEY, 'xxxscrubbedxxx')
        raise BadStatusCodeError('%s: on: %s' % (resp.status_code, url))
    return json.loads(resp.content)


def is_vouched(email):
    content = _fetch_users(email)
    if content:
        for obj in content['results']:
            return obj['is_vouched']
    return False


def fetch_user(email, is_username=False):
    content = _fetch_users(email, is_username=is_username)
    if content:
        for obj in content['results']:
            return _fetch_user(obj['_url'])


def fetch_user_name(email, is_username=False):
    user = fetch_user(email, is_username=is_username)
    if user:
        full_name = user.get('full_name')
        if full_name and full_name['privacy'] == 'Public':
            return full_name['value']


def in_group(email, group):
    if isinstance(group, list):  # pragma: no cover
        raise NotImplementedError('supply a single group name')
    content = _fetch_users(email, group=group)
    return not not content['results']


def _fetch_groups(order_by='name', url=None, name=None):
    if not getattr(settings, 'MOZILLIANS_API_KEY', None):  # pragma no cover
        logging.warning("'MOZILLIANS_API_KEY' not set up.")
        return False

    if not url:
        url = settings.MOZILLIANS_API_BASE + '/api/v2/groups/'
        data = {
            'api-key': settings.MOZILLIANS_API_KEY,
        }
        if name:
            data['name'] = name
        url += '?' + urllib.urlencode(data)

    resp = requests.get(url)
    if resp.status_code != 200:
        url = url.replace(settings.MOZILLIANS_API_KEY, 'xxxscrubbedxxx')
        raise BadStatusCodeError('%s: on: %s' % (resp.status_code, url))
    return json.loads(resp.content)


def get_all_groups(name_search=None):
    all_groups = []
    next_url = None
    while True:
        found = _fetch_groups(name=name_search, url=next_url)
        all_groups.extend(found['results'])
        if len(all_groups) >= found['count']:
            break
        next_url = found['next']
    return all_groups


def get_all_groups_cached(name_search=None, lasting=60 * 60):
    cache_key = 'all_mozillian_groups'
    cache_key_lock = cache_key + 'lock'
    all_groups = cache.get(cache_key)
    if all_groups is None:
        if cache.get(cache_key_lock):
            return []
        cache.set(cache_key_lock, True, 60)
        all_groups = get_all_groups()
        cache.set(cache_key, all_groups, lasting)
        cache.delete(cache_key_lock)
    return all_groups


def get_contributors():
    """Return a list of all users who are in the
    https://mozillians.org/en-US/group/air-mozilla-contributors/ group
    and whose usernames are in the settings.CONTRIBUTORS list.

    Return them in the order of settings.CONTRIBUTORS.
    """
    _users = _fetch_users(group='air mozilla contributors', is_vouched=True)
    # turn that into a dict of username -> url
    urls = dict(
        (x['username'], x['_url'])
        for x in _users['results']
        if x['username'] in settings.CONTRIBUTORS
    )
    users = []
    for username in settings.CONTRIBUTORS:
        if username not in urls:
            continue
        user = _fetch_user(urls[username])
        if not user.get('photo') or user['photo']['privacy'] != 'Public':
            # skip users who don't have a public photo
            continue
        assert user['is_public']
        users.append(user)
    return users
