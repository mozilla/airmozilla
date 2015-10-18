import json

from nose.tools import eq_
import mock

from django.core.urlresolvers import reverse

from .base import ManageTestCase
from airmozilla.base.tests.testbase import Response


class TestAutocompeter(ManageTestCase):

    def test_home_page(self):
        url = reverse('manage:autocompeter')
        response = self.client.get(url)
        eq_(response.status_code, 200)

    @mock.patch('requests.post')
    def test_update(self, rpost):

        def mocked_post(url, **options):
            return Response(
                'OK',
                201
            )

        rpost.side_effect = mocked_post

        url = reverse('manage:autocompeter')
        response = self.client.post(url, {
            'all': True,
            'verbose': True
        })
        eq_(response.status_code, 302)

    @mock.patch('requests.get')
    def test_stats(self, rget):

        def mocked_get(url, **options):
            return Response(
                {'documents': 3},
                200,
                headers={
                    'Content-Type': 'application/json'
                }
            )

        rget.side_effect = mocked_get

        url = reverse('manage:autocompeter_stats')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['documents'], 3)

    @mock.patch('requests.get')
    def test_test(self, rget):

        def mocked_get(url, **options):
            return Response(
                {
                    'terms': [options['params']['q']],
                    'results': [
                        ['/url', 'Page'],
                    ]
                },
                200,
                headers={
                    'Content-Type': 'application/json'
                }
            )

        rget.side_effect = mocked_get

        url = reverse('manage:autocompeter_test')
        response = self.client.get(url, {'term': 'test'})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['terms'], ['test'])
        eq_(data['results'], [['/url', 'Page']])
