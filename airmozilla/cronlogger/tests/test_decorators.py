import sys
from decimal import Decimal

from nose.tools import ok_, eq_

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.cronlogger.models import CronLog
from airmozilla.cronlogger.decorators import capture


@capture
def nothing():
    pass


@capture
def loud():
    print "Something!"


@capture
def complaining():
    print >>sys.stderr, "Not good!"


@capture
def failing():
    print "Something"
    print >>sys.stderr, "Bad"
    raise NameError('crap!')


class TestCaptureDecorator(DjangoTestCase):

    def test_basic(self):
        nothing()
        cr, = CronLog.objects.all()
        eq_(cr.job, 'nothing')
        ok_(cr.created)
        eq_(cr.stdout, '')
        eq_(cr.stderr, '')
        eq_(cr.exc_type, None)
        eq_(cr.exc_value, None)
        eq_(cr.exc_traceback, None)
        ok_(cr.duration is not None)
        ok_(cr.duration <= Decimal('0.001'))

    def test_loud(self):
        loud()
        cr, = CronLog.objects.all()
        eq_(cr.job, 'loud')
        eq_(cr.stdout, 'Something!\n')

    def test_complaining(self):
        complaining()
        cr, = CronLog.objects.all()
        eq_(cr.job, 'complaining')
        eq_(cr.stderr, 'Not good!\n')

    def test_failing(self):
        try:
            failing()
            assert False
        except NameError:
            # we're actually expecting this to happy
            pass
        cr, = CronLog.objects.all()
        eq_(cr.job, 'failing')
        eq_(cr.stderr, 'Bad\n')
        eq_(cr.stdout, 'Something\n')
        ok_(cr.exc_type)
        ok_(cr.exc_value)
        ok_(cr.exc_traceback)
        ok_(cr.duration is not None)
        ok_(cr.duration <= Decimal('0.001'))
