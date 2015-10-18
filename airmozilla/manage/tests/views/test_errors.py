import mock
from nose.tools import eq_, ok_, assert_raises

from django.core.urlresolvers import reverse

from .base import ManageTestCase


class TestErrorTrigger(ManageTestCase):

    def test_trigger_error(self):
        url = reverse('manage:error_trigger')
        response = self.client.get(url)
        assert self.user.is_superuser
        eq_(response.status_code, 200)

        # sans a message
        response = self.client.post(url, {'message': ''})
        eq_(response.status_code, 200)
        ok_('This field is required' in response.content)

        assert_raises(
            NameError,
            self.client.post,
            url,
            {'message': 'Some Message'}
        )

    @mock.patch('airmozilla.manage.views.errors.Client')
    def test_trigger_error_with_raven(self, mocked_client):
        url = reverse('manage:error_trigger')
        assert self.user.is_superuser
        raven_config = {
            'dsn': 'fake123'
        }
        with self.settings(RAVEN_CONFIG=raven_config):
            response = self.client.post(url, {
                'message': 'Some Message',
                'capture_with_raven': True
            })
            eq_(response.status_code, 302)

        mocked_client().captureException.assert_called_with()
