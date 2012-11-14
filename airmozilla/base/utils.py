import time
import datetime
import re
import urllib
import urllib2
import functools
import logging
import json
import subprocess
import xml.etree.ElementTree as ET

import pytz

from django import http
from django.core.cache import cache
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template.defaultfilters import slugify
from django.core.exceptions import ImproperlyConfigured


class EdgecastEncryptionError(Exception):
    pass


class VidlyTokenizeError(Exception):
    pass


def unique_slugify(data, models, duplicate_key=''):
    """Returns a unique slug string.  If duplicate_key is provided, this is
       appended for non-unique slugs before adding a count."""
    slug_base = slugify(data)
    counter = 0
    slug = slug_base
    while any(model.objects.filter(slug=slug).exists() for model in models):
        counter += 1
        if counter == 1 and duplicate_key:
            slug_base += '-' + duplicate_key
            slug = slug_base
            continue
        slug = "%s-%i" % (slug_base, counter)
    return slug


def tz_apply(dt, tz):
    """Returns a datetime with tz applied, timezone-aware.
       Strips the Django-inserted timezone from settings.TIME_ZONE."""
    dt = dt.replace(tzinfo=None)
    return tz.normalize(tz.localize(dt))


# From socorro-crashstats
def json_view(f):
    @functools.wraps(f)
    def wrapper(*args, **kw):
        response = f(*args, **kw)
        if isinstance(response, http.HttpResponse):
            return response
        else:
            return http.HttpResponse(
                _json_clean(json.dumps(response)),
                content_type='application/json; charset=UTF-8'
            )
    return wrapper


def _json_clean(value):
    """JSON-encodes the given Python object."""
    # JSON permits but does not require forward slashes to be escaped.
    # This is useful when json data is emitted in a <script> tag
    # in HTML, as it prevents </script> tags from prematurely terminating
    # the javscript. Some json libraries do this escaping by default,
    # although python's standard library does not, so we do it here.
    # http://stackoverflow.com/questions/1580647/json-why-are-forward\
    # -slashes-escaped
    return value.replace("</", "<\\/")


def paginate(objects, page, count):
    """Returns a set of paginated objects, count per page (on #page)"""
    paginator = Paginator(objects, count)
    try:
        objects_paged = paginator.page(page)
    except PageNotAnInteger:
        objects_paged = paginator.page(1)
    except EmptyPage:
        objects_paged = paginator.page(paginator.num_pages)
    return objects_paged


def vidly_tokenize(tag, seconds):
    cache_key = 'vidly_tokenize:%s' % tag
    token = cache.get(cache_key)
    if token is not None:
        return token

    query = """
    <?xml version="1.0"?>
    <Query>
        <Action>GetSecurityToken</Action>
        <UserID>%(user_id)s</UserID>
        <UserKey>%(user_key)s</UserKey>
        <MediaShortLink>%(tag)s</MediaShortLink>
        <ExpirationTimeSeconds>%(seconds)s</ExpirationTimeSeconds>
    </Query>
    """
    xml = query % {
        'user_id': settings.VIDLY_USER_ID,
        'user_key': settings.VIDLY_USER_KEY,
        'tag': tag,
        'seconds': seconds,
    }

    req = urllib2.Request(
        settings.VIDLY_API_URL,
        urllib.urlencode({'xml': xml.strip()})
    )
    try:
        response = urllib2.urlopen(req)
    except urllib2.URLError:
        logging.error('URLError on opening request', exc_info=True)
        raise VidlyTokenizeError(
            'Temporary network error when trying to fetch Vid.ly token'
        )
    response_content = response.read().strip()
    root = ET.fromstring(response_content)

    success = root.find('Success')
    token = None
    error_code = None
    if success is not None:
        token = success.find('Token').text
    else:
        errors = root.find('Errors')
        if errors is not None:
            error = errors.find('Error')
            error_code = error.find('ErrorCode').text

    if error_code == '8.1':
        # if you get a 8.1 error code it means you tried to get a
        # security token for a vid.ly video that doesn't need to be
        # secure.
        cache.set(cache_key, '', 60 * 60 * 24)
        return ''

    if token:
        # save it for a very short time.
        # it's safer and at least protects us from possible excessive hits
        # over the network.
        cache.set(cache_key, token, 60)
    else:
        logging.error('Unable fetch token for tag %r' % tag)
        logging.info(response_content)

    return token


def unhtml(text_with_html):
    return re.sub('<.*?>', '', text_with_html)


def edgecast_tokenize(seconds=None, **kwargs):
    if not settings.EDGECAST_SECURE_KEY:  # pragma: no cover
        raise ImproperlyConfigured(
            "'EDGECAST_SECURE_KEY' not set up"
        )

    if seconds:
        expires = (
            datetime.datetime.utcnow() +
            datetime.timedelta(seconds=seconds)
        )
        # EdgeCast unfortunately do their timestamps for `ec_expire` based on
        # a local time rather than UTC.
        # So you have to subtract 8 hours (or 7 depending on season) to get
        # a timestamp that works.
        tz = pytz.timezone('America/Los_Angeles')
        expires += tz.utcoffset(expires)
        expires_timestamp = time.mktime(expires.timetuple())
        kwargs['ec_expire'] = int(expires_timestamp)

    key = settings.EDGECAST_SECURE_KEY
    binary_location = getattr(
        settings,
        'BINARY_LOCATION',
        'ec_encrypt'
    )
    command = [
        binary_location,
        key,
        urllib.urlencode(kwargs)
    ]
    out, err = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    ).communicate()

    if not out and err:
        raise EdgecastEncryptionError(err)

    return out.strip()


def vidly_add_media(url, email=None, token_protection=None):
    root = ET.Element('query')
    ET.SubElement(root, 'action').text = 'AddMedia'
    ET.SubElement(root, 'userid').text = settings.VIDLY_USER_ID
    ET.SubElement(root, 'userkey').text = settings.VIDLY_USER_KEY
    if email:
        ET.SubElement(root, 'notify').text = email
    source = ET.SubElement(root, 'Source')
    ET.SubElement(source, 'SourceFile').text = url
    ET.SubElement(source, 'HD').text = 'yes'
    ET.SubElement(source, 'CDN').text = 'AWS'
    if token_protection:
        protect = ET.SubElement(source, 'Protect')
        ET.SubElement(protect, 'Token')

    xml = ET.tostring(root)
    req = urllib2.Request(
        'http://m.vid.ly/api/',
        urllib.urlencode({'xml': xml.strip()})
    )
    response = urllib2.urlopen(req)
    response_content = response.read().strip()
    root = ET.fromstring(response_content)
    success = root.find('Success')
    if success is not None:
        # great!
        return success.find('MediaShortLink').find('ShortLink').text, None
    logging.error(response_content)
    # error!
    return None, response_content
