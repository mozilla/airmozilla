import urllib

import jinja2
from django_jinja import library

from django.contrib.staticfiles.storage import staticfiles_storage
from django.utils.http import urlquote
from django.core.urlresolvers import reverse
from django.template.defaultfilters import linebreaksbr, urlize

from airmozilla.base.utils import get_abs_static


@library.global_function
def static(path):
    return staticfiles_storage.url(path)


@library.filter
def urlencode(txt):
    """Url encode a path."""
    if isinstance(txt, unicode):
        txt = txt.encode('utf-8')
    return urllib.quote_plus(txt)


@library.global_function
def url(viewname, *args, **kwargs):
    """Helper for Django's ``reverse`` in templates."""
    return reverse(viewname, args=args, kwargs=kwargs)


@library.global_function
@jinja2.contextfunction
def abs_static(context, path):
    """Make sure we always return a FULL absolute URL that starts
    with 'http'.
    """
    return get_abs_static(path, context['request'])


@library.global_function
def show_duration(duration, include_seconds=False):
    if isinstance(duration, float):
        # e.g. 16.61 means 16 seconds and 61 milliseconds
        duration, milliseconds = str(duration).split('.')
        duration = int(duration)
    hours = duration / 3600
    seconds = duration % 3600
    minutes = seconds / 60
    seconds = seconds % 60
    out = []
    if hours > 1:
        out.append('%d hours' % hours)
    elif hours:
        out.append('1 hour')
    if minutes > 1:
        out.append('%d minutes' % minutes)
    elif minutes:
        out.append('1 minute')
    if include_seconds or (not hours and not minutes):
        if seconds > 1:
            out.append('%d seconds' % seconds)
        elif seconds:
            out.append('1 second')
    return ' '.join(out)


@library.global_function
def show_duration_compact(duration):
    hours = duration / 3600
    seconds = duration % 3600
    minutes = seconds / 60
    seconds = seconds % 60
    out = []
    if hours:
        out.append('%dh' % hours)
    if hours or minutes:
        out.append('%dm' % minutes)
    if hours or minutes or seconds:
        out.append('%ds' % seconds)
    return ''.join(out)


@library.global_function
def mozillians_permalink(username):
    return 'https://mozillians.org/u/%s' % urlquote(username)


@library.filter
def urlize_and_linebreaksbr(text):
    html = urlize(text)
    html = linebreaksbr(html)
    return html
