from urllib import urlencode

from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model

import mock
from requests.exceptions import ReadTimeout
from nose.tools import ok_, eq_

from airmozilla.base import mozillians
from airmozilla.base.tests.testbase import Response
from airmozilla.main.models import UserProfile, UserEmailAlias
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

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_auth0_callback_staff(self, rget, rpost):

        def mocked_post(url, **kwargs):
            ok_(settings.AUTH0_DOMAIN in url)
            json_ = kwargs['json']
            assert json_['code'] == 'xyz001'  # what we're testing
            eq_(json_['client_id'], settings.AUTH0_CLIENT_ID)
            eq_(json_['client_secret'], settings.AUTH0_SECRET)
            eq_(json_['grant_type'], 'authorization_code')
            return Response({
                'access_token': 'somecrypticaccesstoken',
                'id_token': SAMPLE_ID_TOKEN,
            })

        rpost.side_effect = mocked_post

        email = 'test@{}'.format(settings.ALLOWED_BID[0])

        def mocked_get(url, **kwargs):
            ok_(settings.AUTH0_DOMAIN in url)
            assert 'access_token=somecrypticaccesstoken' in url
            return Response({
                'email': email,
                'family_name': 'Leonard',
                'given_name': 'Rufus',
                'user_id': '1234567890',
                'email_verified': True,
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

        def mocked_post(url, **kwargs):
            return Response({
                'access_token': 'somecrypticaccesstoken',
                'id_token': SAMPLE_ID_TOKEN,
            })

        rpost.side_effect = mocked_post

        email = 'test@neverheardof.biz'

        def mocked_get(url, **kwargs):
            if settings.MOZILLIANS_API_BASE in url:
                return Response(VOUCHED_FOR_USERS)
            return Response({
                'email': email,
                'family_name': 'Leonard',
                'given_name': 'Randalf',
                'user_id': '00000001',
                'email_verified': True,
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

        def mocked_post(url, **kwargs):
            return Response({
                'access_token': 'somecrypticaccesstoken',
            })

        rpost.side_effect = mocked_post

        email = 'test@neverheardof.biz'

        def mocked_get(url, **kwargs):
            if settings.MOZILLIANS_API_BASE in url:
                return Response(VOUCHED_FOR_USERS)
            return Response({
                'email': email,
                'family_name': 'Leonard',
                'given_name': 'Randalf',
                'user_id': '00000001',
                'email_verified': True,
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

        def mocked_post(url, **kwargs):
            return Response({
                'access_token': 'somecrypticaccesstoken',
            })

        rpost.side_effect = mocked_post

        email = 'test@{}'.format(settings.ALLOWED_BID[0])

        def mocked_get(url, **kwargs):
            if settings.MOZILLIANS_API_BASE in url:
                return Response(VOUCHED_FOR_USERS)
            return Response({
                'email': email,
                'family_name': 'Leonard',
                'given_name': 'Randalf',
                'user_id': '00000001',
                'email_verified': True,
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

        def mocked_post(url, **kwargs):
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

        def mocked_post(url, **kwargs):
            return Response({
                'access_token': 'somecrypticaccesstoken',
                'id_token': SAMPLE_ID_TOKEN,
            })

        rpost.side_effect = mocked_post

        def mocked_get(url, **kwargs):
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

        def mocked_post(url, **kwargs):
            return Response({
                'access_token': 'somecrypticaccesstoken',
                'id_token': SAMPLE_ID_TOKEN,
            })

        rpost.side_effect = mocked_post

        email = 'test@neverheardof.biz'

        def mocked_get(url, **kwargs):
            if settings.MOZILLIANS_API_BASE in url:
                return Response(NOT_VOUCHED_FOR_USERS)
            return Response({
                'email': email,
                'family_name': 'Leonard',
                'given_name': 'Randalf',
                'user_id': '00000001',
                'email_verified': True,
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

        def mocked_post(url, **kwargs):
            return Response({
                'access_token': 'somecrypticaccesstoken',
                'id_token': SAMPLE_ID_TOKEN,
            })

        rpost.side_effect = mocked_post

        email = 'test@neverheardof.biz'

        def mocked_get(url, **kwargs):
            if settings.MOZILLIANS_API_BASE in url:
                raise mozillians.BadStatusCodeError(600)
            return Response({
                'email': email,
                'family_name': 'Leonard',
                'given_name': 'Randalf',
                'user_id': '00000001',
                'email_verified': True,
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
    def test_auth0_callback_email_not_verified(self, rget, rpost):

        def mocked_post(url, **kwargs):
            return Response({
                'access_token': 'somecrypticaccesstoken',
                'id_token': SAMPLE_ID_TOKEN,
            })

        rpost.side_effect = mocked_post

        email = 'test@neverheardof.biz'

        def mocked_get(url, **kwargs):
            if settings.MOZILLIANS_API_BASE in url:
                raise mozillians.BadStatusCodeError(600)
            return Response({
                'email': email,
                'family_name': 'Leonard',
                'given_name': 'Randalf',
                'user_id': '00000001',
                'email_verified': False,
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
        ok_('class="signin-link"' in response.content)

        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('class="signin-link"' not in response.content)

    def test_signout(self):
        self._login()
        url = reverse('authentication:signout')
        response = self.client.get(url)
        eq_(response.status_code, 200)
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

        def mocked_post(url, **kwargs):
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

        def mocked_get(url, **kwargs):
            if settings.MOZILLIANS_API_BASE in url:
                return Response(VOUCHED_FOR_USERS)
            return Response({
                'email': email,
                'family_name': 'Leonard',
                'given_name': 'Randalf',
                'user_id': '00000001',
                'email_verified': True,
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

        def mocked_post(url, **kwargs):
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

        def mocked_get(url, **kwargs):
            if settings.MOZILLIANS_API_BASE in url:
                return Response(VOUCHED_FOR_USERS)
            return Response({
                'email': email,
                'family_name': 'Leonard',
                'given_name': 'Randalf',
                'user_id': '00000001',
                'email_verified': True,
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

        def mocked_post(url, **kwargs):
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

        def mocked_get(url, **kwargs):
            if settings.MOZILLIANS_API_BASE in url:
                return Response(VOUCHED_FOR_USERS)
            return Response({
                'email': email,
                'family_name': 'Leonard',
                'given_name': 'Randalf',
                'user_id': '00000001',
                'email_verified': True,
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

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_auth0_callback_was_inactive_was_alias(self, rget, rpost):

        def mocked_post(url, **kwargs):
            return Response({
                'access_token': 'somecrypticaccesstoken',
                'id_token': SAMPLE_ID_TOKEN,
            })

        rpost.side_effect = mocked_post

        email = 'test@neverheardof.biz'
        User.objects.create(
            email=email,
            is_active=False  # Note!
        )
        right_user = User.objects.create(
            username='other',
            email='other@example.com',
        )
        UserEmailAlias.objects.create(
            email=email,
            user=right_user,
        )

        def mocked_get(url, **kwargs):
            if settings.MOZILLIANS_API_BASE in url:
                return Response(VOUCHED_FOR_USERS)
            return Response({
                'email': email,
                'family_name': 'Leonard',
                'given_name': 'Randalf',
                'user_id': '00000001',
                'email_verified': True,
            })

        rget.side_effect = mocked_get

        url = reverse('authentication:callback')
        response = self.client.get(url, {'code': 'xyz001'})
        eq_(response.status_code, 302)
        ok_(response['location'].endswith(settings.AUTH0_SUCCESS_URL))

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_auth0_callback_only_found_as_alias(self, rget, rpost):

        def mocked_post(url, **kwargs):
            return Response({
                'access_token': 'somecrypticaccesstoken',
                'id_token': SAMPLE_ID_TOKEN,
            })

        rpost.side_effect = mocked_post

        email = 'test@neverheardof.biz'
        right_user = User.objects.create(
            username='other',
            email='other@example.com',
        )
        UserEmailAlias.objects.create(
            email=email,
            user=right_user,
        )

        def mocked_get(url, **kwargs):
            if settings.MOZILLIANS_API_BASE in url:
                return Response(VOUCHED_FOR_USERS)
            return Response({
                'email': email,
                'family_name': 'Leonard',
                'given_name': 'Randalf',
                'user_id': '00000001',
                'email_verified': True,
            })

        rget.side_effect = mocked_get

        url = reverse('authentication:callback')
        response = self.client.get(url, {'code': 'xyz001'})
        eq_(response.status_code, 302)
        ok_(response['location'].endswith(settings.AUTH0_SUCCESS_URL))

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_auth0_callback_timed_out_access_token(self, rget, rpost):

        def mocked_post(url, **kwargs):
            return Response({
                'access_token': 'somecrypticaccesstoken',
                'id_token': SAMPLE_ID_TOKEN,
            })

        rpost.side_effect = mocked_post

        email = 'test@neverheardof.biz'
        right_user = User.objects.create(
            username='other',
            email='other@example.com',
        )
        UserEmailAlias.objects.create(
            email=email,
            user=right_user,
        )

        def mocked_get(url, **kwargs):
            assert '?access_token=' in url
            raise ReadTimeout('too long')

        rget.side_effect = mocked_get

        url = reverse('authentication:callback')
        response = self.client.get(url, {'code': 'xyz001'})
        eq_(response.status_code, 302)
        ok_(response['location'].endswith(
            reverse('authentication:signin')
        ))

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_auth0_callback_timed_out_authorization(self, rget, rpost):

        def mocked_post(url, **kwargs):
            assert 'oauth/token' in url
            raise ReadTimeout('too long')

        rpost.side_effect = mocked_post

        email = 'test@neverheardof.biz'
        right_user = User.objects.create(
            username='other',
            email='other@example.com',
        )
        UserEmailAlias.objects.create(
            email=email,
            user=right_user,
        )

        url = reverse('authentication:callback')
        response = self.client.get(url, {'code': 'xyz001'})
        eq_(response.status_code, 302)
        ok_(response['location'].endswith(
            reverse('authentication:signin')
        ))
