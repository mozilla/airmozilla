"""
Used so we can easily debug if cron jobs are being fired.
"""

import datetime

from django.core.cache import cache
from django.core.management.base import NoArgsCommand


class Command(NoArgsCommand):  # pragma: no cover

    def handle(self, **options):
        now = datetime.datetime.utcnow()
        cache.set('cron-ping', now, 60 * 60)
