from nose.tools import eq_, ok_

from django import http
from django.test.client import RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.urlresolvers import reverse

from airmozilla.main.models import UserProfile
from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.authentication.middleware import ValidateIDToken

User = get_user_model()


class TestMiddleware(DjangoTestCase):

    def _get_request(self, path='/', post=False, **headers):
        if post:
            request = RequestFactory(**headers).post(path)
        else:
            request = RequestFactory(**headers).get(path)
        middleware = SessionMiddleware()
        middleware.process_request(request)
        request.session.save()
        return request

    def test_renew_successfully(self):
        self.auth0_renew.side_effect = lambda x: '000.111.222'
        user = User.objects.create(email='test@example.com')
        user_profile = UserProfile.objects.create(
            user=user,
            id_token='12345.6789.01234'
        )
        request = self._get_request()
        request.user = user
        middleware = ValidateIDToken()
        result = middleware.process_request(request)
        eq_(result, None)
        user_profile = UserProfile.objects.get(id=user_profile.id)
        eq_(user_profile.id_token, '000.111.222')

        # The result of that is cached, so even if we change our mock
        # function, it wouldn't be called
        def not_called():
            raise AssertionError

        self.auth0_renew.side_effect = not_called
        result = middleware.process_request(request)
        eq_(result, None)

    def test_renewal_to_log_out(self):
        self.auth0_renew.side_effect = lambda x: None
        user = User.objects.create(email='test@example.com')
        UserProfile.objects.create(
            user=user,
            id_token='12345.6789.01234'
        )
        request = self._get_request()
        request.user = user
        middleware = ValidateIDToken()
        result = middleware.process_request(request)
        # Redirected to the sign in page
        ok_(isinstance(result, http.HttpResponseRedirect))
        eq_(result.url, reverse('authentication:signin'))

    def test_reasons_not_check(self):
        def not_called():
            raise AssertionError

        self.auth0_renew.side_effect = not_called
        user = User.objects.create(email='test@example.com')
        UserProfile.objects.create(
            user=user,
            id_token='12345.6789.01234'
        )

        # Doesn't kick in on post requests
        request = self._get_request(post=True)
        request.user = user
        middleware = ValidateIDToken()
        result = middleware.process_request(request)
        eq_(result, None)

        # Or AJAX requests
        request = self._get_request(HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = user
        middleware = ValidateIDToken()
        result = middleware.process_request(request)
        eq_(result, None)

        # Or if you're not active anyway
        user.is_active = False
        request = self._get_request()
        request.user = user
        middleware = ValidateIDToken()
        result = middleware.process_request(request)
        eq_(result, None)

        # Or if you're anonymous
        request = self._get_request()
        request.user = AnonymousUser()
        middleware = ValidateIDToken()
        result = middleware.process_request(request)
        eq_(result, None)

        # Or if you're on the authentication callback URL
        user.is_active = True
        request = self._get_request(reverse('authentication:callback'))
        request.user = user
        middleware = ValidateIDToken()
        result = middleware.process_request(request)
        eq_(result, None)
