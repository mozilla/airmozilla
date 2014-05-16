import locale
import time
import datetime
import urllib
import json

import jinja2

from django.utils.text import Truncator
from django.utils.timezone import utc
from django.db.utils import IntegrityError
from django.contrib.sites.models import RequestSite

from jingo import register
from sorl.thumbnail import get_thumbnail

from airmozilla.base.utils import html_to_text


@register.filter
def js_date(dt, format='ddd, MMM D, YYYY, h:mma UTCZZ', enable_timeago=True,
            autoupdate=False):
    """ Python datetime to a time tag with JS Date.parse-parseable format. """
    dt = dt.replace(microsecond=0)  # we don't need the microseconds
    dt_date = dt.strftime('%m/%d/%Y')
    dt_time = dt.strftime('%H:%M')
    dt_tz = dt.tzname() or 'UTC'
    formatted_datetime = ' '.join([dt_date, dt_time, dt_tz])
    class_ = 'timeago ' if enable_timeago else ''
    if autoupdate:
        class_ += 'autoupdate '
    return jinja2.Markup('<time datetime="%s" class="%sjstime"'
                         ' data-format="%s">%s</time>'
                         % (dt.isoformat(), class_,
                            format, formatted_datetime))


@register.function
def date_now():
    """The current date in UTC."""
    return datetime.datetime.utcnow().replace(tzinfo=utc, microsecond=0)


@register.function
def short_desc(event, words=25, strip_html=False):
    """Takes an event object and returns a shortened description."""
    if event.short_description:
        return event.short_description
    description = event.description
    if strip_html:
        description = html_to_text(description)
    return Truncator(description).words(words)


@register.function
def truncate_words(text, words):
    return Truncator(text).words(words)


@register.function
def truncate_chars(text, chars):
    assert chars > 4, chars
    if len(text) > chars:
        text = '%s...' % text[:chars - 3].strip()
    return text


@register.function
def thumbnail(filename, geometry, **options):
    try:
        return get_thumbnail(filename, geometry, **options)
    except IOError:
        return None
    except IntegrityError:
        # annoyingly, this happens sometimes because kvstore in sorl
        # doesn't check before writing properly
        # see https://bugzilla.mozilla.org/show_bug.cgi?id=817765
        # try again
        time.sleep(1)
        return thumbnail(filename, geometry, **options)


@register.function
def tags_query_string(tags):
    return urllib.urlencode({'tag': [x.name for x in tags]}, True)


@register.filter
def carefulnl2br(string):
    # if the string contains existing paragraphs or line breaks
    # in html...
    if '<p' in string or '<br' in string:
        # ...then dare not
        return string
    return string.replace('\n', '<br>')


@register.function
def thousands(number):
    """AKA ``thousands separator'' - 1000000 becomes 1,000,000 """
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except locale.Error:
        locale.setlocale(locale.LC_ALL, '')
    return locale.format('%d', number, True)


@register.function
def make_absolute(uri, request):
    if '://' not in uri:
        prefix = request.is_secure() and 'https' or 'http'
        uri = '%s://%s%s' % (prefix, RequestSite(request).domain, uri)
    return uri


@register.filter
def pluralize(value, form='s'):
    if value != 1:
        return form
    return ''


@register.filter
def json_print(value):
    return jinja2.Markup(json.dumps(value))
