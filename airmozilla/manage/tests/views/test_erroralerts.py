from nose.tools import ok_

from django.core.urlresolvers import reverse

from .base import ManageTestCase


class TestErrorAlerts(ManageTestCase):

    def test_new_template_with_error(self):
        url = reverse('manage:template_new')
        response = self.client.get(url)
        ok_('Form errors!' not in response.content)
        response = self.client.post(url, {
            'name': '',
            'content': 'hello!'
        })
        ok_('Form errors!' in response.content)
