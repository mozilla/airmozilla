import datetime
import time

import jinja2
from nose.tools import ok_, eq_

from django.test import TestCase

from airmozilla.main.models import Event
from airmozilla.manage.templatetags.jinja_helpers import (
    almost_equal,
    event_status_to_css_label,
    format_message,
    formatduration,
    highlight_stopwords,
    highlight_matches,
)


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


class MiscTests(TestCase):

    def test_event_status_to_css_label(self):
        label = event_status_to_css_label(Event.STATUS_REMOVED)
        eq_(label, 'label-danger')
        label = event_status_to_css_label(Event.STATUS_INITIATED)
        eq_(label, 'label-default')
        label = event_status_to_css_label(Event.STATUS_SCHEDULED)
        eq_(label, 'label-success')
        label = event_status_to_css_label(Event.STATUS_PENDING)
        eq_(label, 'label-primary')

    def test_format_message(self):
        result = format_message('bla')
        eq_(result, 'bla')
        ok_(isinstance(result, jinja2.Markup))

        # or it's an object
        class M(object):
            message = 'ble'
        m = M()
        eq_(format_message(m), 'ble')

        # or a message containing a markdown style relative
        result = format_message("Go [to](/page.html)")
        eq_(
            result,
            'Go <a href="/page.html" class="message-inline">to</a>'
        )
        ok_(isinstance(result, jinja2.Markup))

    def test_formatduration(self):
        output = formatduration(10)
        eq_(output, '10s')
        output = formatduration(60)
        eq_(output, u'1m\xa00s')
        output = formatduration(70)
        eq_(output, u'1m\xa010s')
        output = formatduration(60 * 60)
        eq_(output, u'1h\xa00m\xa00s')
        output = formatduration(60 * 60 + 61)
        eq_(output, u'1h\xa01m\xa01s')

    def test_highlight_stopwords(self):
        result = highlight_stopwords(
            'This is the - break point'
        )
        ok_(isinstance(result, jinja2.Markup))
        ok_('<span class="stopword">This</span>' in result)
        ok_('<span class="not-stopword">break</span>' in result)

    def test_highlight_matches(self):
        result = highlight_matches(
            'This: is the - "break" po&int',
            'this not break or pointing'
        )
        ok_(isinstance(result, jinja2.Markup))
        ok_('<span class="match">This:</span>' in result)
        ok_('<span class="stopword">is</span>' in result)
        ok_('<span class="stopword">the</span>' in result)
        ok_('<span class="match">&#34;break&#34;</span>' in result)
        ok_('po&int' not in result)
        ok_('po&amp;int' in result)
