from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse

from .base import ManageTestCase


class TestTasksTester(ManageTestCase):

    def test_dashboard(self):
        url = reverse('manage:tasks_tester')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        response = self.client.post(url, {'milliseconds': 84})
        eq_(response.status_code, 302)

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Waited 0 seconds :)' in response.content)
