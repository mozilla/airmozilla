import re
import urllib
import urllib2
import functools
import logging
import json
import xml.etree.ElementTree as ET

from django import http
from django.core.cache import cache
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template.defaultfilters import slugify


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


def tz_apply(datetime, tz):
    """Returns a datetime with tz applied, timezone-aware.
       Strips the Django-inserted timezone from settings.TIME_ZONE."""
    datetime = datetime.replace(tzinfo=None)
    return tz.normalize(tz.localize(datetime))


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


def vidly_tokenize(tag, expiration_seconds):
    cache_key = 'vidly_tokenize:%s' % tag
    token = cache.get(cache_key)
    if token is not None:
        return token

    URL = 'http://m.vid.ly/api/'
    query = """
    <?xml version="1.0"?>
    <Query>
        <Action>GetSecurityToken</Action>
        <UserID>%(user_id)s</UserID>
        <UserKey>%(user_key)s</UserKey>
        <MediaShortLink>%(tag)s</MediaShortLink>
        <ExpirationTimeSeconds>%(expiration_seconds)s</ExpirationTimeSeconds>
    </Query>
    """
    xml = query % {
        'user_id': settings.VIDLY_USER_ID,
        'user_key': settings.VIDLY_USER_KEY,
        'tag': tag,
        'expiration_seconds': expiration_seconds,
    }

    req = urllib2.Request(
        URL,
        urllib.urlencode({'xml': xml.strip()})
    )
    response = urllib2.urlopen(req)
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

    if not token:
        logging.error('Unable fetch token for tag %r' % tag)
        logging.info(response_content)

    return token


def unhtml(text_with_html):
    return re.sub('<.*?>', '', text_with_html)
