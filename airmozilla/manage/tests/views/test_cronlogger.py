import json
from decimal import Decimal

from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse

from airmozilla.cronlogger.models import CronLog
from .base import ManageTestCase


class TestCronLogger(ManageTestCase):

    def test_home_page(self):
        url = reverse('manage:cronlogger')
        response = self.client.get(url)
        eq_(response.status_code, 200)

    def test_cronlogger_data(self):
        url = reverse('manage:cronlogger_data')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['count'], 0)
        eq_(data['jobs'], [])
        eq_(data['logs'], [])

        CronLog.objects.create(
            job='foo',
            duration=Decimal('0.1'),
        )
        CronLog.objects.create(
            job='bar',
            stdout='Out',
            duration=Decimal('1.1'),
        )
        CronLog.objects.create(
            job='bar',
            exc_type='NameError',
            exc_value='Value',
            exc_traceback='Traceback',
            duration=Decimal('10.1'),
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['count'], 3)
        eq_(
            data['jobs'],
            [
                {'text': 'bar (2)', 'value': 'bar'},
                {'text': 'foo (1)', 'value': 'foo'}
            ]
        )
        last = data['logs'][0]
        ok_(last['created'])
        eq_(last['exc_type'], 'NameError')
        eq_(last['exc_value'], 'Value')
        eq_(last['exc_traceback'], 'Traceback')
        eq_(last['duration'], 10.1)

        # lastly we filter
        response = self.client.get(url, {'job': 'foo'})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['count'], 1)
