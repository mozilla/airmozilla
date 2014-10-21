import datetime

from django.core.cache import cache

import cronjobs

from airmozilla.cronlogger.decorators import capture
from . import tweeter
from . import pestering
from . import event_hit_stats
from . import archiver
from . import videoinfo


@cronjobs.register
@capture
def send_unsent_tweets():
    tweeter.send_unsent_tweets()


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
    archiver.auto_archive()


@cronjobs.register
@capture
def update_event_hit_stats():
    event_hit_stats.update(
        cap=15,
        swallow_errors=True,
    )


@cronjobs.register
@capture
def fetch_durations():
    videoinfo.fetch_durations(
        max_=10,
        verbose=True
    )
