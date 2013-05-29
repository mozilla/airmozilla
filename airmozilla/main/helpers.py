import locale
import time
import datetime
import urllib
import jinja2

from django.utils.text import truncate_words as _truncate_words
from django.utils.timezone import utc
from django.db.utils import IntegrityError

from jingo import register
from sorl.thumbnail import get_thumbnail

from airmozilla.base.utils import html_to_text


@register.filter
def js_date(dt, format='ddd, MMM D, YYYY, h:mma UTCZZ', enable_timeago=True,
            autoupdate=False):
    """ Python datetime to a time tag with JS Date.parse-parseable format. """
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
    return _truncate_words(description, words)


@register.function
def truncate_words(*args, **kwargs):
    return _truncate_words(*args, **kwargs)


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
