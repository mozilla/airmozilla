import datetime
import jinja2

from django.utils.text import truncate_words
from django.utils.timezone import utc

from jingo import register
from sorl.thumbnail import get_thumbnail


@register.filter
def js_date(dt, format='ddd, MMM D, YYYY, h:mma UTCZZ', enable_timeago=True):
    """ Python datetime to a time tag with JS Date.parse-parseable format. """
    dt_date = dt.strftime('%m/%d/%Y')
    dt_time = dt.strftime('%H:%M')
    dt_tz = dt.tzname() or 'UTC'
    formatted_datetime = ' '.join([dt_date, dt_time, dt_tz])
    timeago = 'timeago ' if enable_timeago else ''
    return jinja2.Markup('<time datetime="%s" class="%sjstime"'
                          ' data-format="%s">%s</time>'
                 % (dt.isoformat(), timeago, format, formatted_datetime))


@register.function
def date_now():
    """The current date in UTC."""
    return datetime.datetime.utcnow().replace(tzinfo=utc, microsecond=0)


@register.function
def short_desc(event, words=25):
    """Takes an event object and returns a shortened description."""
    return event.short_description or truncate_words(event.description, words)


@register.function
def thumbnail(filename, geometry, **options):
    try:
        return get_thumbnail(filename, geometry, **options)
    except IOError:
        return None
