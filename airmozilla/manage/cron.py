import datetime

from django.core.cache import cache

import cronjobs

from .tweeter import send_unsent_tweets as _send_unsent_tweets
from .pestering import pester
from . import archiver


@cronjobs.register
def send_unsent_tweets():
    _send_unsent_tweets()


@cronjobs.register
def pester_approvals():
    pester()


@cronjobs.register
def cron_ping():
    now = datetime.datetime.utcnow()
    cache.set('cron-ping', now, 60 * 60)


@cronjobs.register
def auto_archive():
    archiver.auto_archive()
