import time
import datetime
import re
import urllib
import subprocess
import os
import urlparse
import random

import pytz
import requests
from slugify import slugify

from django.core.handlers.wsgi import WSGIRequest
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import ImproperlyConfigured
from django.contrib.sites.requests import RequestSite
from django.contrib.sites.models import Site
from django.core.mail.backends.filebased import EmailBackend
from django.forms.utils import ErrorList
from django.contrib.staticfiles.storage import staticfiles_storage

from airmozilla.base.akamai_token_v2 import AkamaiToken


STOPWORDS = (
    "a able about across after all almost also am among an and "
    "any are as at be because been but by can cannot could dear "
    "did do does either else ever every for from get got had has "
    "have he her hers him his how however i if in into is it its "
    "just least let like likely may me might most must my "
    "neither no nor not of off often on only or other our own "
    "rather said say says she should since so some than that the "
    "their them then there these they this tis to too twas us "
    "wants was we were what when where which while who whom why "
    "will with would yet you your".split()
)


def roughly(number, variance_percentage=20):
    """return a number that is roughly what you inputted but
    slightly smaller or slightly bigger.

    For example, if you feed it 100, return 96 or 117 or 91 or 102.
    Basically, take or add a certain percentage to the number.

    This is useful if you stuff a lot of stuff in the cache and don't
    want them all to expire at the same time but instead stagger
    the expiration times a bit.
    """
    percentage = random.randint(-variance_percentage, variance_percentage)
    return int(number * (1 + percentage / 100.0))


def simplify_form_errors(errors):
    copy = {}
    for key, value in errors.items():
        if isinstance(value, ErrorList):
            value = list(value)
        copy[key] = value
    return copy


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
    response = requests.get(
        settings.BITLY_URL,
        params={
            'access_token': settings.BITLY_ACCESS_TOKEN,
            'longUrl': url
        }
    )
    result = response.json()
    if result.get('status_code') == 500:
        raise ValueError(result.get('status_txt'))
    return result['data']['url']


def unique_slugify(data, models, duplicate_key='', lower=True, exclude=None):
    """Returns a unique slug string.  If duplicate_key is provided, this is
       appended for non-unique slugs before adding a count."""
    slug_base = slugify(data)
    if lower:
        slug_base = slug_base.lower()
    counter = 0
    slug = slug_base

    def query(model):
        qs = model.objects.filter(slug=slug)
        if exclude:
            qs = qs.exclude(**exclude)
        return qs

    while any(query(model).exists() for model in models):
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


def akamai_tokenize(
    window_seconds=180,
    token_name='hdnea',
    start_time='now',
    ip=None,
    url=None,
    access_list='/*/*_Restricted/*',
    key=None,
    escape_early=False,
    verbose=False,
    **other
):
    config = other
    config['key'] = key or settings.AKAMAI_SECURE_KEY
    assert config['key'], "no key set up"
    config['window_seconds'] = window_seconds
    config['start_time'] = start_time
    config['token_name'] = token_name
    config['ip'] = ip
    config['acl'] = access_list
    config['verbose'] = verbose
    config['escape_early'] = escape_early
    generator = AkamaiToken(**config)
    token = generator.generateToken()
    return token


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


def get_abs_static(path, request):
    path = staticfiles_storage.url(path)
    prefix = request.is_secure() and 'https' or 'http'

    if path.startswith('/') and not path.startswith('//'):
        # e.g. '/media/foo.png'
        root_url = get_base_url(request)
        path = root_url + path

    if path.startswith('//'):
        path = '%s:%s' % (prefix, path)

    assert path.startswith('http://') or path.startswith('https://')
    return path


def get_base_url(request):
    return (
        '%s://%s' % (
            request.is_secure() and 'https' or 'http',
            RequestSite(request).domain
        )
    )


def prepare_vidly_video_url(url):
    """Return the URL prepared for Vid.ly
    See # See http://help.encoding.com/knowledge-base/article/\
    save-some-time-on-your-encodes/

    Hopefully this will make the transcoding faster.
    """
    if 's3.amazonaws.com' in url:
        if '?' in url:
            url += '&'
        else:
            url += '?'
        url += 'nocopy'
    return url


def build_absolute_url(uri):
    site = Site.objects.get_current()
    base = 'https://%s' % site.domain  # yuck!
    return urlparse.urljoin(base, uri)
