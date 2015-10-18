from cStringIO import StringIO

import mock
from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse

from airmozilla.main.models import Event
from .base import ManageTestCase
from airmozilla.manage.tests.test_vidly import SAMPLE_MEDIALIST_XML


class TestDurations(ManageTestCase):

    @mock.patch('urllib2.urlopen')
    def test_durations(self, p_urlopen):
        event = Event.objects.get(title='Test event')
        event.template_environment = {'tag': 'abc123'}
        event.save()
        event.template.name = 'Vid.ly'
        event.template.save()
        assert event in Event.objects.archived()

        def mocked_urlopen(request):
            return StringIO(SAMPLE_MEDIALIST_XML.strip())

        p_urlopen.side_effect = mocked_urlopen

        url = reverse('manage:durations_report_all')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.title in response.content)
        # the fixture (SAMPLE_MEDIALIST_XML) says it's 350 seconds
        eq_(response.content.count('5 minutes 50 seconds'), 1)
        ok_('n/a' in response.content)

        event.duration = 300
        event.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('n/a' not in response.content)
        # now there should be a link visible to the events duration page
        duration_url = reverse('manage:event_edit_duration', args=(event.id,))
        ok_(duration_url in response.content)

        event.duration = 350
        event.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(duration_url not in response.content)
        eq_(response.content.count('5 minutes 50 seconds'), 2)
