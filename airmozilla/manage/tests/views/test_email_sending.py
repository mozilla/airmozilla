from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse
from django.conf import settings

from .base import ManageTestCase


class TestEmailSending(ManageTestCase):

    def test_durations(self):
        url = reverse('manage:email_sending')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(settings.EMAIL_BACKEND in response.content)

        # let's actually send something
        data = {
            'to': '   ; ',  # deliberately junk
            'subject': 'Some Subject',
            'html_body': '<p><b>Some Html Body</p>',
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 200)
        # should have errored
        ok_('has-error' in response.content)

        data['to'] = 'foo@bar'
        response = self.client.post(url, data)
        eq_(response.status_code, 200)
        ok_('has-error' not in response.content)
        # This should show the sent email too

        def html_quote(s):
            return s.replace('<', '&lt;').replace('>', '&gt;')

        ok_(html_quote(data['html_body']) in response.content)
