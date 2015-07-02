import datetime

from django.core.cache import cache

import cronjobs

from airmozilla.cronlogger.decorators import capture
from . import tweeter
from . import pestering
from . import event_hit_stats
from . import archiver
from . import videoinfo
from . import vidly_synchronization
from . import autocompeter
from . import related


@cronjobs.register
@capture
def send_unsent_tweets():
    tweeter.send_unsent_tweets(verbose=True)


@cronjobs.register
@capture
def pester_approvals():
    pestering.pester()


@cronjobs.register
@capture
def cron_ping():
    now = datetime.datetime.utcnow()
    cache.set('cron-ping', now, 60 * 60)


@cronjobs.register
@capture
def auto_archive():
    archiver.auto_archive(verbose=True)


@cronjobs.register
@capture
def update_event_hit_stats():
    event_hit_stats.update(
        cap=25,
        swallow_errors=True,
    )


@cronjobs.register
@capture
def fetch_durations():
    videoinfo.fetch_durations(
        max_=3,
        verbose=True,
    )


@cronjobs.register
@capture
def import_screencaptures():
    videoinfo.import_screencaptures(
        verbose=True,
    )


@cronjobs.register
@capture
def fetch_screencaptures():
    videoinfo.fetch_screencaptures(
        max_=2,
        verbose=True,
        import_if_possible=True,
        save_locally_some=True,
    )


@cronjobs.register
@capture
def synchronize_vidly_submissions():
    vidly_synchronization.synchronize_all(verbose=True)


@cronjobs.register
@capture
def tweet_new_published_events():
    tweeter.tweet_new_published_events(verbose=True)


@cronjobs.register
@capture
def autocompeter_reset():
    autocompeter.update(
        verbose=True,
        all=True,
        flush_first=True
    )


@cronjobs.register
@capture
def autocompeter_update():
    autocompeter.update(
        # this number is supposed to match that of the cronjob itself
        since=datetime.timedelta(minutes=10)
    )


@cronjobs.register
# @capture
def related_content_reindex():
    related.index(all=True, flush_first=True)


@cronjobs.register
# @capture
def related_content_index():
    related.index()
