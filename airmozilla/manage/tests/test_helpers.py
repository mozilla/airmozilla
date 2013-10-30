import datetime
import time

from nose.tools import ok_

from django.test import TestCase

from airmozilla.manage.helpers import almost_equal


class TestAlmostEqual(TestCase):

    def test_almost_equal(self):
        date1 = datetime.datetime.now()
        time.sleep(0.001)
        date2 = datetime.datetime.now()
        assert date1 != date2
        ok_(almost_equal(date1, date2))
        ok_(almost_equal(date2, date1))

    def test_almost_equal_different_days(self):
        date1 = date2 = datetime.datetime.now()
        date2 += datetime.timedelta(days=1)
        ok_(not almost_equal(date1, date2))
        ok_(not almost_equal(date2, date1))

    def test_not_equal_but_close(self):
        date1 = date2 = datetime.datetime.now()
        date2 += datetime.timedelta(seconds=1)
        ok_(not almost_equal(date1, date2))
        ok_(not almost_equal(date2, date1))
