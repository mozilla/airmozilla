import time
import datetime
import re
import urllib
import functools
import json
import subprocess

import html2text
import pytz

from django import http
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template.defaultfilters import slugify
from django.core.exceptions import ImproperlyConfigured


class EdgecastEncryptionError(Exception):
    pass


def shorten_url(url):
    """return the URL shortened with Bit.ly"""
    if not settings.BITLY_ACCESS_TOKEN:
        raise ImproperlyConfigured('BITLY_ACCESS_TOKEN not set')
    bitly_base_url = 'https://api-ssl.bitly.com/v3/shorten'
    qs = urllib.urlencode({
        'access_token': settings.BITLY_ACCESS_TOKEN,
        'longUrl': url
    })
    bitly_url = '%s?%s' % (bitly_base_url, qs)
    response = urllib.urlopen(bitly_url).read()
    result = json.loads(response)
    if result.get('status_code') == 500:
        raise ValueError(result.get('status_txt'))
    return result['data']['url']


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


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)


# From socorro-crashstats
def json_view(f):
    @functools.wraps(f)
    def wrapper(*args, **kw):
        response = f(*args, **kw)
        if isinstance(response, http.HttpResponse):
            return response
        else:
            return http.HttpResponse(
                _json_clean(json.dumps(response, cls=DateTimeEncoder)),
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


def html_to_text(html):
    # in case the HTML doesn't already do all its newlines by
    # paragraphs or <br> tags, then convert newlines to <br>
    # tags
    if not ('<p' in html or '<br' in html):
        html = html.replace('\n\n', '<br>')
    return html2text.html2text(html)
