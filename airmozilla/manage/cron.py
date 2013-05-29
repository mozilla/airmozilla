import datetime

from django.core.cache import cache

import cronjobs

from .tweeter import send_unsent_tweets as _send_unsent_tweets
from .pestering import pester
from .archiver import archive
from airmozilla.main.models import Event


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
    events = (
        Event.objects
        .filter(status=Event.STATUS_PENDING,
                archive_time__isnull=True,
                template__name__contains='Vid.ly')
    )
    for event in events:
        archive(event, swallow_email_exceptions=True)
