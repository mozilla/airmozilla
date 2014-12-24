import time
import os
import stat
import logging

import twython

from django.core.exceptions import ImproperlyConfigured
from django.utils.importlib import import_module
from django.utils import timezone
from django.conf import settings
from django.db.models import Q

from airmozilla.main.helpers import thumbnail
from airmozilla.main.models import EventTweet, Event, Approval


def send_unsent_tweets():
    # this is what the cron job can pipe into

    def is_approved(event):
        return (
            not Approval.objects
            .filter(event=event, approved=False)
            .count()
        )

    now = timezone.now()
    query = Q(sent_date__isnull=True) | Q(error__isnull=False)
    qs = (
        EventTweet.objects
        .filter(event__status=Event.STATUS_SCHEDULED)
        .filter(send_date__lte=now)
        .filter(query)
        .order_by('id')
    )

    for event_tweet in qs:
        approved = (
            not Approval.objects
            .filter(event=event_tweet.event, approved=False)
            .count()
        )
        if approved:
            send_tweet(event_tweet)


def send_tweet(event_tweet, save=True):
    if event_tweet.include_placeholder:
        thumb = thumbnail(
            event_tweet.event.placeholder_img,
            '300x300'
        )
        file_path = thumb.storage.path(thumb.name)
    else:
        file_path = None

    text = event_tweet.text
    # due to a bug in twython
    # https://github.com/ryanmcgrath/twython/issues/154
    # we're not able to send non-ascii characters properly
    # Hopefully this can go away sometime soon.
    text = text.encode('utf-8')
    try:
        tweet_id = _send(text, file_path=file_path)
        event_tweet.tweet_id = tweet_id
        event_tweet.error = None
    except Exception, msg:
        logging.error("Failed to send tweet", exc_info=True)
        event_tweet.error = str(msg)
    now = timezone.now()
    event_tweet.sent_date = now
    save and event_tweet.save()


def _send(text, file_path=None):
    if file_path:
        assert os.path.isfile(file_path), file_path

    t0 = time.time()
    if getattr(settings, 'TWEETER_BACKEND', None):
        try:
            path = settings.TWEETER_BACKEND
            mod_name, klass_name = path.rsplit('.', 1)
            mod = import_module(mod_name)
        except ImportError, e:
            raise ImproperlyConfigured(
                'Error importing email backend module %s: "%s"'
                % (mod_name, e)
            )
        try:
            tweeter_backend = getattr(mod, klass_name)
        except AttributeError:
            raise ImproperlyConfigured(
                'Module "%s" does not define a '
                '"%s" class' % (mod_name, klass_name)
            )
    else:
        tweeter_backend = twython.Twython

    twitter = tweeter_backend(
        twitter_token=settings.TWITTER_CONSUMER_KEY,
        twitter_secret=settings.TWITTER_CONSUMER_SECRET,
        oauth_token=settings.TWITTER_ACCESS_TOKEN,
        oauth_token_secret=settings.TWITTER_ACCESS_TOKEN_SECRET
    )
    t1 = time.time()
    logging.info("Took %s seconds to connect to Twitter" % (t1 - t0))

    t0 = time.time()
    if file_path:
        new_entry = twitter.updateStatusWithMedia(
            file_path,
            status=text
        )
    else:
        new_entry = twitter.updateStatus(
            status=text
        )
    t1 = time.time()
    logging.info("Took %s seconds to tweet with media" % (t1 - t0))

    return new_entry['id']


class ConsoleTweeter(object):  # pragma: no cover
    """Available so that you can redirect actual tweets to print stuff on
    stdout instead.
    """

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def updateStatusWithMedia(self, file_path, status):
        if file_path:
            from django.template.defaultfilters import filesizeformat
            import textwrap
            print file_path.ljust(50),
            print filesizeformat(os.stat(file_path)[stat.ST_SIZE])
            indent = ' ' * 8
            print '\n'.join(
                textwrap.wrap(
                    status,
                    initial_indent=indent,
                    subsequent_indent=indent
                )
            )

        from random import randint
        return {'id': str(randint(1000000, 10000000))}

    def updateStatus(self, status):
        return self.updateStatusWithMedia(None, status)
