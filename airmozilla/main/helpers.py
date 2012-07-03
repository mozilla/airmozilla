import datetime
import jinja2

from django.utils.text import truncate_words
from django.utils.timezone import utc

from jingo import register


@register.filter
def js_date(dt, format='ddd, MMM D, YYYY, h:mma UTCZZ'):
    """ Python datetime to a time tag with JS Date.parse-parseable format. """
    dt_date = dt.strftime('%m/%d/%Y')
    dt_time = dt.strftime('%H:%M')
    dt_tz = dt.tzname() or 'UTC'
    formatted_datetime = ' '.join([dt_date, dt_time, dt_tz])
    return jinja2.Markup('<time datetime="%s" class="jstime"'
                          ' data-format="%s">%s</time>'
                 % (dt.isoformat(), format, formatted_datetime))


@register.function
def date_now():
    """The current date in UTC."""
    return datetime.datetime.utcnow().replace(tzinfo=utc, microsecond=0)


@register.function
def short_desc(event, words=25):
    """Takes an event object and returns a shortened description."""
    # We use an event object instead of a description itself
    # so in the future, we could use a human-shortened version if provided.
    return truncate_words(event.description, words)
