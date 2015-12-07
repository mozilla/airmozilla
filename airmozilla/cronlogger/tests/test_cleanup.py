import datetime

from nose.tools import eq_

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.cronlogger.models import CronLog
from airmozilla.cronlogger import cleanup


class TestCleanup(DjangoTestCase):

    def test_purge_old(self):
        log = CronLog.objects.create(
            job='anything',
        )
        cleanup.purge_old()
        eq_(CronLog.objects.all().count(), 1)

        then = datetime.timedelta(days=1)
        log.created -= then
        log.save()
        cleanup.purge_old(delta=then)
        eq_(CronLog.objects.all().count(), 0)
