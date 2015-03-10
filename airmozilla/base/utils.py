import time
import datetime
import re
import urllib
import json
import subprocess
import os

import html2text
import pytz
from slugify import slugify

from django.core.handlers.wsgi import WSGIRequest
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import ImproperlyConfigured
from django.contrib.sites.models import RequestSite
from django.core.mail.backends.filebased import EmailBackend


class EmlEmailBackend(EmailBackend):
    """
    The django.core.mail.backends.filebased.EmailBackend backend
    is neat but it creates the files as .log.
    This makes it not possible to open the files in Postbox until
    you rename them.

    To use this, put this in your settings/local.py::

        EMAIL_BACKEND = 'airmozilla.base.utils.EmlEmailBackend'
        EMAIL_FILE_PATH = '/Users/peterbe/tmp/captured-emails/'

    """
    def _get_filename(self):
        """Return a unique file name."""
        if self._fname is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            fname = "%s-%s.eml" % (timestamp, abs(id(self)))
            self._fname = os.path.join(self.file_path, fname)
        return self._fname


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


def unique_slugify(data, models, duplicate_key='', lower=True):
    """Returns a unique slug string.  If duplicate_key is provided, this is
       appended for non-unique slugs before adding a count."""
    slug_base = slugify(data)
    if lower:
        slug_base = slug_base.lower()
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


def paginate(objects, page, count):
    """Returns a set of paginated objects, count per page (on #page)"""
    __, objects_paged = paginator(objects, page, count)
    return objects_paged


def paginator(objects, page, count):
    """return a Paginator instance and the objects paged"""
    paginator_ = Paginator(objects, count)
    try:
        objects_paged = paginator_.page(page)
    except PageNotAnInteger:
        objects_paged = paginator_.page(1)
    except EmptyPage:
        objects_paged = paginator_.page(paginator_.num_pages)
    return paginator_, objects_paged


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


def fix_base_url(base_url):
    """because most of the functions in this file can take either a
    base_url (string) or a request, we make this easy with a quick
    fixing function."""
    if isinstance(base_url, WSGIRequest):
        request = base_url
        protocol = 'https' if request.is_secure() else 'http'
        base_url = '%s://%s' % (protocol, RequestSite(request).domain)
    return base_url


class _DotDict(dict):

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self._recurse(self)

    def _recurse(self, item):
        for key, value in item.iteritems():
            if isinstance(value, dict):
                item[key] = _DotDict(value)

    def __getattr__(self, key):
        if key.startswith('__'):
            raise AttributeError(key)
        return self[key]


def dot_dict(d):
    return _DotDict(d)


def get_base_url(request):
    return (
        '%s://%s' % (
            request.is_secure() and 'https' or 'http',
            RequestSite(request).domain
        )
    )
