import re
import cgi
import urllib
import urlparse as _urlparse

import jinja2
from django_jinja import library

from django.template import Context
from django.template.loader import get_template
from django.conf import settings
from django.utils.timesince import timesince as _timesince
from django.utils.html import avoid_wrapping

from bootstrapform.templatetags.bootstrap import bootstrap_horizontal

from airmozilla.base.utils import STOPWORDS
from airmozilla.main.models import Event, EventOldSlug
from airmozilla.comments.models import Comment


@library.global_function
def bootstrapform(form):
    template = get_template("bootstrapform/form.html")
    context = Context({'form': form})
    return template.render(context)


@library.global_function
def bootstrapform_horizontal(form):
    return bootstrap_horizontal(form, 'col-sm-2 col-lg-2')


@library.global_function
def invalid_form(form):
    """return true if the form is bound and invalid"""
    return form.is_bound and not form.is_valid()


@library.global_function
def query_string(request, **kwargs):
    current = request.META.get('QUERY_STRING')
    parsed = cgi.parse_qs(current)
    parsed.update(kwargs)
    return urllib.urlencode(parsed, True)


@library.global_function
def clashes_with_event(url):
    """used for URLs belonging to Flatpages to see if their
    URL is possibly clashing with an event.
    """
    possible = url.split('/', 2)[1]
    try:
        return Event.objects.get(slug=possible)
    except Event.DoesNotExist:
        try:
            return EventOldSlug.objects.get(slug=possible).event
        except EventOldSlug.DoesNotExist:
            return False


@library.global_function
def full_tweet_url(tweet_id):
    if not getattr(settings, 'TWITTER_USERNAME', None):  # pragma: no cover
        # if it's not configured, there can't be a full URL
        return
    return (
        'https://twitter.com/%s/status/%s'
        % (
            settings.TWITTER_USERNAME,
            tweet_id
        )
    )


@library.global_function
def scrub_transform_passwords(text):
    for password in settings.URL_TRANSFORM_PASSWORDS.values():
        text = text.replace(
            password,
            'XXXpasswordhiddenXXX'
        )
    return text


@library.global_function
def timesince(start_time):
    return _timesince(start_time)


basic_markdown_link = re.compile(
    '(\[(.*?)\]\((/.*?)\))'
)


@library.global_function
def format_message(message):
    if hasattr(message, 'message'):
        # it's a django.contrib.messages.base.Message instance
        message = message.message

    if basic_markdown_link.findall(message):
        whole, label, link = basic_markdown_link.findall(message)[0]
        message = message.replace(
            whole,
            '<a href="%s" class="message-inline">%s</a>'
            % (link, label)
        )

    message = jinja2.Markup(message)

    return message


@library.global_function
def almost_equal(date1, date2):
    """return true if the only difference between these two dates are
    their microseconds."""
    diff = abs(date1 - date2)
    return not diff.seconds and not diff.days


@library.global_function
def comment_status_to_css_label(status):
    # because this just got too messy in the template
    if status == Comment.STATUS_APPROVED:
        return 'label-success'
    elif status == Comment.STATUS_REMOVED:
        return 'label-danger'
    return 'label-info'


@library.global_function
def event_status_to_css_label(status):
    if status in (Event.STATUS_INITIATED, Event.STATUS_SUBMITTED):
        return 'label-default'
    if status in (Event.STATUS_PENDING, Event.STATUS_PROCESSING):
        return 'label-primary'
    if status == Event.STATUS_SCHEDULED:
        return 'label-success'
    if status == Event.STATUS_REMOVED:
        return 'label-danger'
    raise NotImplementedError(status)


@library.global_function
def urlparse(url):
    return _urlparse.urlparse(url)


@library.filter
def formatduration(seconds):
    if seconds is None:
        return ""
    parts = []
    if seconds >= 60:
        minutes = seconds / 60
        if seconds >= 60 * 60:
            hours = seconds / 3600
            minutes = (seconds % 3600) / 60
            parts.append('%dh' % hours)
        seconds = seconds % 60
        parts.append('%dm' % minutes)
    parts.append('%ds' % seconds)
    return avoid_wrapping(' '.join(parts))


@library.global_function
def highlight_stopwords(text, class_='stopword', not_class='not-stopword'):
    words = []
    for word in text.split():
        if word.lower() in STOPWORDS or word in '-?':
            css_class = class_
        else:
            css_class = not_class

        words.append('<span class="%s">%s</span>' % (
            css_class,
            jinja2.escape(word)
        ))
    return jinja2.Markup(' '.join(words))


@library.global_function
def highlight_matches(text, base, class_='match', stopword_class='stopword'):

    def clean_word(s):
        for char in '"\'():|[]{}':
            s = s.replace(char, '')
        return s

    base_tokens = [clean_word(x) for x in base.lower().split()]
    words = []
    tokens = text.split()
    for word in tokens:
        if clean_word(word.lower()) in base_tokens:
            css_class = class_
        elif clean_word(word.lower()) in STOPWORDS or word in '-?':
            css_class = stopword_class
        else:
            css_class = ''
        if css_class:
            words.append('<span class="%s">%s</span>' % (
                css_class,
                jinja2.escape(word)
            ))
        else:
            words.append(jinja2.escape(word))
    return jinja2.Markup(' '.join(words))
