from django.conf import settings
from django.test import TestCase

from funfactory.urlresolvers import reverse

from airmozilla.auth.browserid_mock import mock_browserid


class TestViews(TestCase):
    def _login_attempt(self, email, assertion='fakeassertion123'):
        with mock_browserid(email):
            r = self.client.post(reverse('auth:mozilla_browserid_verify'),
                                 {'assertion': assertion})
        return r

    def test_invalid(self):
        """Bad BrowserID form (i.e. no assertion) -> failure."""
        response = self._login_attempt(None, None)
        self.assertRedirects(response,
                             reverse(settings.LOGIN_REDIRECT_URL_FAILURE))

    def test_bad_verification(self):
        """Bad verification -> failure."""
        response = self._login_attempt(None)
        self.assertRedirects(response,
                             reverse(settings.LOGIN_REDIRECT_URL_FAILURE))

    def test_nonmozilla(self):
        """Non-Mozilla email -> failure."""
        response = self._login_attempt('tmickel@mit.edu')
        self.assertRedirects(response,
                             reverse(settings.LOGIN_REDIRECT_URL_FAILURE))

    def test_mozilla(self):
        """Mozilla email -> success."""
        # Try the first allowed domain
        response = self._login_attempt('tmickel@' + settings.ALLOWED_BID[0])
        self.assertRedirects(response,
                             reverse(settings.LOGIN_REDIRECT_URL))
