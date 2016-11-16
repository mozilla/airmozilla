import time

import mock
from nose.tools import eq_

from django.test import TestCase

from airmozilla.base.tests.testbase import Response
from airmozilla.authentication import auth0


class TestAuth0(TestCase):
    """Use django.test.TestCase because
    airmozilla.base.tests.testbase.DjangoTestCase heavily mocks
    the function airmozilla.authentication.auth0.renew_id_token"""

    @mock.patch('requests.post')
    def test_renew_id_token(self, rpost):

        def mocked_post(url, json):
            return Response({
                'id_token': 'xzy.123.456',
                'expires': int(time.time()) + 1000,
            })

        rpost.side_effect = mocked_post

        result = auth0.renew_id_token('1234')
        eq_(result, 'xzy.123.456')

    @mock.patch('requests.post')
    def test_renew_id_token_unauthorized(self, rpost):

        def mocked_post(url, json):
            return Response({
                'error_message': 'Not valid!',
            }, status_code=401)

        rpost.side_effect = mocked_post

        result = auth0.renew_id_token('1234')
        eq_(result, None)

    @mock.patch('requests.post')
    def test_renew_id_token_not_json_response(self, rpost):

        def mocked_post(url, json):
            return Response(
                'The world is broken!',
                status_code=500,
                require_valid_json=True
            )

        rpost.side_effect = mocked_post

        result = auth0.renew_id_token('1234')
        eq_(result, None)
