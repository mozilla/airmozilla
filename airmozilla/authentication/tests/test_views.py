import json
from urllib import urlencode
from importlib import import_module

from django.conf import settings
# from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model

import mock
from nose.tools import ok_, eq_

from airmozilla.authentication.browserid_mock import mock_browserid
from airmozilla.base import mozillians
from airmozilla.base.tests.testbase import Response
from airmozilla.main.models import UserProfile
from airmozilla.base.tests.testbase import DjangoTestCase

from airmozilla.base.tests.test_mozillians import (
    VOUCHED_FOR_USERS,
    NOT_VOUCHED_FOR_USERS,
)


User = get_user_model()


SAMPLE_ID_TOKEN = (
    'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJodHRwczovL3BldGVyYmVjb2'
    '0uYXV0aDAuY29tLyIsInN1YiI6Imdvb2dsZS1vYXV0aDJ8MTE2ODU0ODcyNjg2Njc3NjIxN'
    'zA5IiwiYXVkIjoib3hFZUtwTnJmd0RqZm15Y2ZVTXBFekxROE9sNno4R0MiLCJleHAiOjE0'
    'Nzg2MzEzMTgsImlhdCI6MTQ3ODYyNzcxOCwiYXpwIjoib3hFZUtwTnJmd0RqZm15Y2ZVTXB'
    'FekxROE9sNno4R0MifQ._3-ucQUslT51uWKbPlyV-TiiMLuGv4fXV1IVyJgCfo4'
)


class TestViews(DjangoTestCase):

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

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_auth0_callback_staff(self, rget, rpost):

        def mocked_post(url, json):
            ok_(settings.AUTH0_DOMAIN in url)
            assert json['code'] == 'xyz001'  # what we're testing
            eq_(json['client_id'], settings.AUTH0_CLIENT_ID)
            eq_(json['client_secret'], settings.AUTH0_SECRET)
            eq_(json['grant_type'], 'authorization_code')
            return Response({
                'access_token': 'somecrypticaccesstoken',
                'id_token': SAMPLE_ID_TOKEN,
            })

        rpost.side_effect = mocked_post

        email = 'test@{}'.format(settings.ALLOWED_BID[0])

        def mocked_get(url):
            ok_(settings.AUTH0_DOMAIN in url)
            assert 'access_token=somecrypticaccesstoken' in url
            return Response({
                'email': email,
                'family_name': 'Leonard',
                'given_name': 'Rufus',
                'user_id': '1234567890',
            })

        rget.side_effect = mocked_get

        url = reverse('authentication:callback')
        response = self.client.get(url, {'code': 'xyz001'})
        eq_(response.status_code, 302)
        ok_(response['location'].endswith(settings.AUTH0_SUCCESS_URL))

        user = User.objects.get(
            email=email,
            first_name='Rufus',
            last_name='Leonard',
        )
        eq_(
            user.profile.id_token,
            SAMPLE_ID_TOKEN
        )

        # Load the home page, if it worked, the page (header nav)
        # should say our first name.
        response = self.client.get('/')
        eq_(response.status_code, 200)
        ok_('Rufus' in response.content)

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_auth0_callback_contributor(self, rget, rpost):

        def mocked_post(url, json):
            return Response({
                'access_token': 'somecrypticaccesstoken',
                'id_token': SAMPLE_ID_TOKEN,
            })

        rpost.side_effect = mocked_post

        email = 'test@neverheardof.biz'

        def mocked_get(url):
            if settings.MOZILLIANS_API_BASE in url:
                return Response(VOUCHED_FOR_USERS)
            return Response({
                'email': email,
                'family_name': 'Leonard',
                'given_name': 'Randalf',
                'user_id': '00000001',
            })

        rget.side_effect = mocked_get

        url = reverse('authentication:callback')
        response = self.client.get(url, {'code': 'xyz001'})
        eq_(response.status_code, 302)
        ok_(response['location'].endswith(settings.AUTH0_SUCCESS_URL))

        user = User.objects.get(
            email=email,
            first_name='Randalf',
            last_name='Leonard',
        )
        ok_(user.profile.contributor)
        eq_(
            user.profile.id_token,
            SAMPLE_ID_TOKEN
        )

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_auth0_callback_contributor_no_id_token(self, rget, rpost):

        def mocked_post(url, json):
            return Response({
                'access_token': 'somecrypticaccesstoken',
            })

        rpost.side_effect = mocked_post

        email = 'test@neverheardof.biz'

        def mocked_get(url):
            if settings.MOZILLIANS_API_BASE in url:
                return Response(VOUCHED_FOR_USERS)
            return Response({
                'email': email,
                'family_name': 'Leonard',
                'given_name': 'Randalf',
                'user_id': '00000001',
            })

        rget.side_effect = mocked_get

        url = reverse('authentication:callback')
        response = self.client.get(url, {'code': 'xyz001'})
        eq_(response.status_code, 302)
        ok_(response['location'].endswith(settings.AUTH0_SUCCESS_URL))

        user = User.objects.get(
            email=email,
            first_name='Randalf',
            last_name='Leonard',
        )
        ok_(user.profile.contributor)
        eq_(user.profile.id_token, None)

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_auth0_callback_staff_no_id_token(self, rget, rpost):

        def mocked_post(url, json):
            return Response({
                'access_token': 'somecrypticaccesstoken',
            })

        rpost.side_effect = mocked_post

        email = 'test@{}'.format(settings.ALLOWED_BID[0])

        def mocked_get(url):
            if settings.MOZILLIANS_API_BASE in url:
                return Response(VOUCHED_FOR_USERS)
            return Response({
                'email': email,
                'family_name': 'Leonard',
                'given_name': 'Randalf',
                'user_id': '00000001',
            })

        rget.side_effect = mocked_get

        url = reverse('authentication:callback')
        response = self.client.get(url, {'code': 'xyz001'})
        eq_(response.status_code, 302)
        # If you get redirected to the sign in page, it failed
        ok_(response['location'].endswith(
            reverse('authentication:signin')
        ))

    def test_auth0_callback_missing_code(self):
        url = reverse('authentication:callback')
        response = self.client.get(url)
        eq_(response.status_code, 400)

    @mock.patch('requests.post')
    def test_auth0_callback_bad_access_code(self, rpost):

        def mocked_post(url, json):
            return Response({
                'error': 'not right',
            })

        rpost.side_effect = mocked_post

        email = 'test@neverheardof.biz'

        url = reverse('authentication:callback')
        response = self.client.get(url, {'code': 'xyz001'})
        eq_(response.status_code, 302)
        ok_(response['location'].endswith(
            reverse('authentication:signin')
        ))

        ok_(not User.objects.filter(email=email).exists())

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_auth0_callback_bad_access_token(self, rget, rpost):

        def mocked_post(url, json):
            return Response({
                'access_token': 'somecrypticaccesstoken',
                'id_token': SAMPLE_ID_TOKEN,
            })

        rpost.side_effect = mocked_post

        def mocked_get(url):
            return Response('', status_code=600)  # anything but 200

        rget.side_effect = mocked_get

        email = 'test@neverheardof.biz'

        url = reverse('authentication:callback')
        response = self.client.get(url, {'code': 'xyz001'})
        eq_(response.status_code, 302)
        ok_(response['location'].endswith(
            reverse('authentication:signin')
        ))

        ok_(not User.objects.filter(email=email).exists())

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_auth0_callback_contributor_not_vouched(self, rget, rpost):

        def mocked_post(url, json):
            return Response({
                'access_token': 'somecrypticaccesstoken',
                'id_token': SAMPLE_ID_TOKEN,
            })

        rpost.side_effect = mocked_post

        email = 'test@neverheardof.biz'

        def mocked_get(url):
            if settings.MOZILLIANS_API_BASE in url:
                return Response(NOT_VOUCHED_FOR_USERS)
            return Response({
                'email': email,
                'family_name': 'Leonard',
                'given_name': 'Randalf',
                'user_id': '00000001',
            })

        rget.side_effect = mocked_get

        url = reverse('authentication:callback')
        response = self.client.get(url, {'code': 'xyz001'})
        eq_(response.status_code, 302)
        ok_(response['location'].endswith(
            reverse('authentication:signin')
        ))
        ok_(not User.objects.filter(email=email).exists())

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_auth0_callback_mozillians_api_failing(self, rget, rpost):

        def mocked_post(url, json):
            return Response({
                'access_token': 'somecrypticaccesstoken',
                'id_token': SAMPLE_ID_TOKEN,
            })

        rpost.side_effect = mocked_post

        email = 'test@neverheardof.biz'

        def mocked_get(url):
            if settings.MOZILLIANS_API_BASE in url:
                raise mozillians.BadStatusCodeError(600)
            return Response({
                'email': email,
                'family_name': 'Leonard',
                'given_name': 'Randalf',
                'user_id': '00000001',
            })

        rget.side_effect = mocked_get

        url = reverse('authentication:callback')
        response = self.client.get(url, {'code': 'xyz001'})
        eq_(response.status_code, 302)
        ok_(response['location'].endswith(
            reverse('authentication:signin')
        ))
        ok_(not User.objects.filter(email=email).exists())

    def test_signin_page(self):
        url = reverse('authentication:signin')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('class="login-lock"' in response.content)

        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('class="login-lock"' not in response.content)

    def test_signout(self):
        self._login()
        url = reverse('authentication:signout')
        response = self.client.get(url)
        eq_(response.status_code, 405)
        response = self.client.post(url)
        eq_(response.status_code, 302)
        ok_(settings.AUTH0_DOMAIN in response['location'])
        ok_(urlencode({
            'returnTo': settings.AUTH_SIGNOUT_URL,
        }) in response['location'])
        ok_(urlencode({
            'client_id': settings.AUTH0_CLIENT_ID,
        }) in response['location'])

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_auth0_callback_contributor_vouched_was_staff(self, rget, rpost):

        def mocked_post(url, json):
            return Response({
                'access_token': 'somecrypticaccesstoken',
                'id_token': SAMPLE_ID_TOKEN,
            })

        rpost.side_effect = mocked_post

        email = 'test@neverheardof.biz'
        user = User.objects.create(
            email=email,
        )
        user_profile = UserProfile.objects.create(
            user=user,
            contributor=False,
        )

        def mocked_get(url):
            if settings.MOZILLIANS_API_BASE in url:
                return Response(VOUCHED_FOR_USERS)
            return Response({
                'email': email,
                'family_name': 'Leonard',
                'given_name': 'Randalf',
                'user_id': '00000001',
            })

        rget.side_effect = mocked_get

        url = reverse('authentication:callback')
        response = self.client.get(url, {'code': 'xyz001'})
        eq_(response.status_code, 302)
        ok_(response['location'].endswith(settings.AUTH0_SUCCESS_URL))

        user_profile = UserProfile.objects.get(id=user_profile.id)
        ok_(user_profile.contributor)

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_auth0_callback_staff_was_contributor(self, rget, rpost):

        def mocked_post(url, json):
            return Response({
                'access_token': 'somecrypticaccesstoken',
                'id_token': SAMPLE_ID_TOKEN,
            })

        rpost.side_effect = mocked_post

        email = 'test@neverheardof.biz'
        user = User.objects.create(
            email=email,
        )
        user_profile = UserProfile.objects.create(
            user=user,
            contributor=True,
        )

        def mocked_get(url):
            if settings.MOZILLIANS_API_BASE in url:
                return Response(VOUCHED_FOR_USERS)
            return Response({
                'email': email,
                'family_name': 'Leonard',
                'given_name': 'Randalf',
                'user_id': '00000001',
            })

        rget.side_effect = mocked_get

        url = reverse('authentication:callback')
        new_allowed_bid = settings.ALLOWED_BID + ('neverheardof.biz',)
        with self.settings(ALLOWED_BID=new_allowed_bid):
            response = self.client.get(url, {'code': 'xyz001'})
            eq_(response.status_code, 302)
            ok_(response['location'].endswith(settings.AUTH0_SUCCESS_URL))

        user_profile = UserProfile.objects.get(id=user_profile.id)
        ok_(not user_profile.contributor)

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_auth0_callback_staff_was_inactive(self, rget, rpost):

        def mocked_post(url, json):
            return Response({
                'access_token': 'somecrypticaccesstoken',
                'id_token': SAMPLE_ID_TOKEN,
            })

        rpost.side_effect = mocked_post

        email = 'test@neverheardof.biz'
        user = User.objects.create(
            email=email,
            is_active=False  # Note!
        )
        UserProfile.objects.create(
            user=user,
            contributor=True,
        )

        def mocked_get(url):
            if settings.MOZILLIANS_API_BASE in url:
                return Response(VOUCHED_FOR_USERS)
            return Response({
                'email': email,
                'family_name': 'Leonard',
                'given_name': 'Randalf',
                'user_id': '00000001',
            })

        rget.side_effect = mocked_get

        url = reverse('authentication:callback')
        response = self.client.get(url, {'code': 'xyz001'})
        eq_(response.status_code, 302)
        ok_(response['location'].endswith(
            reverse('authentication:signin')
        ))

    def test_auth0_callback_error(self):
        url = reverse('authentication:callback')
        response = self.client.get(url, {
            'error': 'xyz001',
            'error_description': 'Your kind is not welcome here',
        })
        eq_(response.status_code, 302)
        ok_(response['location'].endswith(
            reverse('authentication:signin')
        ))

        # If you now load the signin page, there's a message there for you
        response = self.client.get(reverse('authentication:signin'))
        eq_(response.status_code, 200)
        ok_('Your kind is not welcome here' in response.content)
