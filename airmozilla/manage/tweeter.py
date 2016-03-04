import datetime
import time
import os
import stat
import logging
import urlparse
from importlib import import_module

import twython

from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone
from django.contrib.sites.models import Site
from django.conf import settings
from django.db.models import Q
from django.db import transaction
from django.core.urlresolvers import reverse

from airmozilla.main.templatetags.jinja_helpers import thumbnail
from airmozilla.main.models import EventTweet, Event, Approval
from airmozilla.base.utils import shorten_url, unhtml


def send_unsent_tweets(verbose=False):
    # this is what the cron job can pipe into

    now = timezone.now()
    query = Q(sent_date__isnull=True) | Q(error__isnull=False)
    qs = (
        EventTweet.objects
        .filter(event__status=Event.STATUS_SCHEDULED)
        .filter(send_date__lte=now)
        .filter(failed_attempts__lt=settings.MAX_TWEET_ATTEMPTS)
        .filter(query)
        .order_by('id')
    )

    for event_tweet in qs:

        approved = (
            not Approval.objects
            .filter(event=event_tweet.event, approved=False)
            .exists()
        )
        if verbose:  # pragma: no cover
            print "Event", repr(event_tweet.event)
            print "Approved?", approved
            print "Text", repr(event_tweet.text)
            print "Includ placeholder", event_tweet.include_placeholder
            print "Send date", event_tweet.send_date
            print "Failed attempts", event_tweet.failed_attempts
            print
        if approved:
            sent = send_tweet(event_tweet)
            if verbose:  # pragma: no cover
                print "\tSent?", sent
                if sent:
                    print "\tID", event_tweet.tweet_id
                    print "\tURL", (
                        'https://twitter.com/%s/status/%s' % (
                            settings.TWITTER_USERNAME,
                            event_tweet.tweet_id
                        )
                    )


def send_tweet(event_tweet, save=True):
    if event_tweet.include_placeholder:
        if event_tweet.event.picture:
            pic = event_tweet.event.picture.file
        else:
            pic = event_tweet.event.placeholder_img
        thumb = thumbnail(
            pic,
            '385x218',  # 16/9 ratio
            crop='center'
        )
        file_path = thumb.storage.path(thumb.name)
    else:
        file_path = None

    try:
        tweet_id = _send(event_tweet.text, file_path=file_path)
        event_tweet.tweet_id = tweet_id
        event_tweet.error = None
    except Exception, msg:
        logging.error("Failed to send tweet", exc_info=True)
        event_tweet.error = str(msg)
        event_tweet.failed_attempts += 1
    now = timezone.now()
    event_tweet.sent_date = now
    save and event_tweet.save()

    return not event_tweet.error


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
        app_key=settings.TWITTER_CONSUMER_KEY,
        app_secret=settings.TWITTER_CONSUMER_SECRET,
        oauth_token=settings.TWITTER_ACCESS_TOKEN,
        oauth_token_secret=settings.TWITTER_ACCESS_TOKEN_SECRET
    )
    t1 = time.time()
    logging.info("Took %s seconds to connect to Twitter" % (t1 - t0))

    t0 = time.time()
    if file_path:
        with open(file_path, 'rb') as f:
            media_upload = twitter.upload_media(media=f)
            new_entry = twitter.update_status(
                status=text,
                media_ids=media_upload['media_id']
            )
    else:
        new_entry = twitter.update_status(
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

    def update_status_with_media(self, file_path, status):
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

    def update_status(self, status):
        return self.update_status_with_media(None, status)


@transaction.atomic
def tweet_new_published_events(verbose=False):
    """Create EventTweet instances for events that have recently been
    published and are ready for public consumption."""
    now = timezone.now()
    events = Event.objects.scheduled().filter(
        created__gt=now - datetime.timedelta(days=7),
        created__lt=now,
        privacy=Event.PRIVACY_PUBLIC,
    ).approved().exclude(
        id__in=EventTweet.objects.values('event_id')
    )

    site = Site.objects.get_current()
    base_url = 'https://%s' % site.domain  # yuck!
    for event in events:
        if event.channels.filter(no_automated_tweets=True):
            if verbose:
                print "Skipping", repr(event.title), "because it's part of"
                print event.channels.filter(no_automated_tweets=True)
            continue
        # we have to try to manually create an appropriate tweet
        url = reverse('main:event', args=(event.slug,))
        abs_url = urlparse.urljoin(base_url, url)
        try:
            abs_url = shorten_url(abs_url)
        except (ImproperlyConfigured, ValueError) as err:  # pragma: no cover
            if verbose:  # pragma: no cover
                print "Failed to shorten URL"
                print err

        text = event.title
        if len(text) > 115:
            # Why not 140?
            # We've found that sometimes when you're trying to tweet
            # a piece of text that actually is less than 140 when
            # doing text+URL you can get strange errors from Twitter
            # that it's still too long.
            text = text[:115]

        text = unhtml('%s\n%s' % (
            text,
            abs_url
        ))
        text += '\n'
        tags = (
            event.tags.all()
            .extra(
                select={'lower_name': 'lower(name)'}
            ).order_by('lower_name')
        )
        for tag in tags:
            _tag = '#' + tag.name.replace(' ', '')
            # see comment above why we use 115 instead of 140
            if len(text + _tag) + 1 < 115:
                text += '%s ' % _tag
            else:
                break
        text = text.strip()

        if event.start_time > timezone.now():
            send_date = event.start_time - datetime.timedelta(minutes=30)
        else:
            send_date = timezone.now()  # send as soon as possible
        event_tweet = EventTweet.objects.create(
            event=event,
            text=text,
            include_placeholder=True,
            send_date=send_date,
        )
        if verbose:  # pragma: no cover
            print "Created", repr(event_tweet)
