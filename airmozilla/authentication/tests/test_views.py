import json
from importlib import import_module

from django.conf import settings
from django.test import TestCase
from django.core.urlresolvers import reverse

import mock
from nose.tools import ok_, eq_

from airmozilla.authentication.browserid_mock import mock_browserid
from airmozilla.base import mozillians
from airmozilla.base.tests.testbase import Response
from airmozilla.main.models import UserProfile

from airmozilla.base.tests.test_mozillians import (
    VOUCHED_FOR_USERS,
    NOT_VOUCHED_FOR_USERS,
)


class TestViews(TestCase):

    def setUp(self):
        super(TestViews, self).setUp()

        engine = import_module(settings.SESSION_ENGINE)
        store = engine.SessionStore()
        store.save()  # we need to make load() work, or the cookie is worthless
        self.client.cookies[settings.SESSION_COOKIE_NAME] = store.session_key

    def shortDescription(self):
        # Stop nose using the test docstring and instead the test method name.
        pass

    def get_messages(self):
        return self.client.session['_messages']

    def _login_attempt(self, email, assertion='fakeassertion123', next=None):
        if not next:
            next = '/'
        with mock_browserid(email):
            post_data = {
                'assertion': assertion,
                'next': next
            }
            return self.client.post(
                '/browserid/login/',
                post_data
            )

    def test_invalid(self):
        """Bad BrowserID form (i.e. no assertion) -> failure."""
        response = self._login_attempt(None, None)
        eq_(response['content-type'], 'application/json')
        redirect = json.loads(response.content)['redirect']
        eq_(redirect, settings.LOGIN_REDIRECT_URL_FAILURE)
        # self.assertRedirects(
        #     response,
        #     settings.LOGIN_REDIRECT_URL_FAILURE + '?bid_login_failed=1'
        # )

    def test_bad_verification(self):
        """Bad verification -> failure."""
        response = self._login_attempt(None)
        eq_(response['content-type'], 'application/json')
        redirect = json.loads(response.content)['redirect']
        eq_(redirect, settings.LOGIN_REDIRECT_URL_FAILURE)
        # self.assertRedirects(
        #    response,
        #    settings.LOGIN_REDIRECT_URL_FAILURE + '?bid_login_failed=1'
        # )

    @mock.patch('requests.get')
    def test_nonmozilla(self, rget):
        """Non-Mozilla email -> failure."""
        def mocked_get(url, **options):
            if 'tmickel' in url:
                return Response(NOT_VOUCHED_FOR_USERS)
            if 'peterbe' in url:
                return Response(VOUCHED_FOR_USERS)
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        response = self._login_attempt('tmickel@mit.edu')
        eq_(response['content-type'], 'application/json')
        redirect = json.loads(response.content)['redirect']
        eq_(redirect, settings.LOGIN_REDIRECT_URL_FAILURE)
        # self.assertRedirects(
        #     response,
        #     settings.LOGIN_REDIRECT_URL_FAILURE + '?bid_login_failed=1'
        # )

        # now with a non-mozillian that is vouched for
        response = self._login_attempt('peterbe@gmail.com')
        eq_(response['content-type'], 'application/json')
        redirect = json.loads(response.content)['redirect']
        eq_(redirect, settings.LOGIN_REDIRECT_URL)
        # self.assertRedirects(response,
        #                      settings.LOGIN_REDIRECT_URL)

    @mock.patch('requests.get')
    def test_nonmozilla_vouched_for_second_time(self, rget):
        assert not UserProfile.objects.all()

        def mocked_get(url, **options):
            return Response(VOUCHED_FOR_USERS)

        rget.side_effect = mocked_get

        # now with a non-mozillian that is vouched for
        response = self._login_attempt('peterbe@gmail.com')
        eq_(response['content-type'], 'application/json')
        redirect = json.loads(response.content)['redirect']
        eq_(redirect, settings.LOGIN_REDIRECT_URL)
        # self.assertRedirects(response,
        #                      settings.LOGIN_REDIRECT_URL)

        # should be logged in
        response = self.client.get('/')
        eq_(response.status_code, 200)
        ok_('Sign in' not in response.content)
        ok_('Sign out' in response.content)

        profile, = UserProfile.objects.all()
        ok_(profile.contributor)

        # sign out
        response = self.client.get(reverse('browserid.logout'))
        eq_(response.status_code, 405)
        response = self.client.post(reverse('browserid.logout'))
        eq_(response.status_code, 200)
        eq_(response['content-type'], 'application/json')
        redirect = json.loads(response.content)['redirect']
        eq_(redirect, settings.LOGIN_REDIRECT_URL)

        # should be logged out
        response = self.client.get('/')
        eq_(response.status_code, 200)
        ok_('Sign in' in response.content)
        ok_('Sign out' not in response.content)

        # sign in again
        response = self._login_attempt('peterbe@gmail.com')
        eq_(response['content-type'], 'application/json')
        redirect = json.loads(response.content)['redirect']
        eq_(redirect, settings.LOGIN_REDIRECT_URL)
        # self.assertRedirects(response,
        #                      settings.LOGIN_REDIRECT_URL)
        # should not have created another one
        eq_(UserProfile.objects.all().count(), 1)

        # sign out again
        response = self.client.post(reverse('browserid.logout'))
        eq_(response.status_code, 200)
        eq_(response['content-type'], 'application/json')
        redirect = json.loads(response.content)['redirect']
        eq_(redirect, settings.LOGIN_REDIRECT_URL)

        # pretend this is lost
        profile.contributor = False
        profile.save()
        response = self._login_attempt('peterbe@gmail.com')
        eq_(response['content-type'], 'application/json')
        redirect = json.loads(response.content)['redirect']
        eq_(redirect, settings.LOGIN_REDIRECT_URL)

        # self.assertRedirects(response,
        #                      settings.LOGIN_REDIRECT_URL)
        # should not have created another one
        eq_(UserProfile.objects.filter(contributor=True).count(), 1)

    def test_mozilla(self):
        """Mozilla email -> success."""
        # Try the first allowed domain
        response = self._login_attempt('tmickel@' + settings.ALLOWED_BID[0])
        eq_(response['content-type'], 'application/json')
        redirect = json.loads(response.content)['redirect']
        eq_(redirect, settings.LOGIN_REDIRECT_URL)

    @mock.patch('requests.get')
    def test_was_contributor_now_mozilla_bid(self, rget):
        """Suppose a user *was* a contributor but now her domain name
        is one of the allowed ones, it should undo that contributor status
        """
        assert not UserProfile.objects.all()

        def mocked_get(url, **options):
            return Response(VOUCHED_FOR_USERS)

        rget.side_effect = mocked_get
        response = self._login_attempt('peterbe@gmail.com')
        eq_(response['content-type'], 'application/json')
        redirect = json.loads(response.content)['redirect']
        eq_(redirect, settings.LOGIN_REDIRECT_URL)

        response = self.client.get('/')
        eq_(response.status_code, 200)
        ok_('Sign in' not in response.content)
        ok_('Sign out' in response.content)

        profile = UserProfile.objects.get(user__email='peterbe@gmail.com')
        ok_(profile.contributor)

        self.client.logout()
        response = self.client.get('/')
        eq_(response.status_code, 200)
        ok_('Sign in' in response.content)
        ok_('Sign out' not in response.content)

        with self.settings(ALLOWED_BID=settings.ALLOWED_BID + ('gmail.com',)):
            response = self._login_attempt('peterbe@gmail.com')
            eq_(response['content-type'], 'application/json')
            redirect = json.loads(response.content)['redirect']
            eq_(redirect, settings.LOGIN_REDIRECT_URL)

        profile = UserProfile.objects.get(user__email='peterbe@gmail.com')
        ok_(not profile.contributor)  # fixed!

    @mock.patch('airmozilla.authentication.views.logger')
    @mock.patch('requests.get')
    def test_nonmozilla_mozillians_unhappy(self, rget, rlogger):
        assert not UserProfile.objects.all()

        def mocked_get(url, **options):
            raise mozillians.BadStatusCodeError('crap!')

        rget.side_effect = mocked_get

        # now with a non-mozillian that is vouched for
        response = self._login_attempt('peterbe@gmail.com')
        eq_(response['content-type'], 'application/json')
        redirect = json.loads(response.content)['redirect']
        eq_(redirect, settings.LOGIN_REDIRECT_URL_FAILURE)
        # self.assertRedirects(
        #     response,
        #     settings.LOGIN_REDIRECT_URL_FAILURE + '?bid_login_failed=1'
        # )
        eq_(rlogger.error.call_count, 1)
