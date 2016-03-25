import cgi
import json
import urlparse

from nose.tools import eq_
import mock

from django.core.cache import cache
from django.core.urlresolvers import reverse

from airmozilla.base.tests.testbase import DjangoTestCase, Response


class TestCuratedGroups(DjangoTestCase):

    def tearDown(self):
        super(TestCuratedGroups, self).tearDown()
        cache.clear()

    @mock.patch('logging.error')
    @mock.patch('requests.get')
    def test_curated_groups_autocomplete(self, rget, rlogging):

        def mocked_get(url, **options):
            params = cgi.parse_qs(urlparse.urlparse(url).query)
            if (
                params.get('name') == ['GROUP NUMBER 1'] or
                params.get('name__icontains') == ['GROUP NUMBER 1']
            ):
                return Response({
                    'count': 1,
                    'results': [
                        {
                            'id': 99,
                            'url': 'https://muzillians.fake/en-US/group/99/',
                            'name': 'GROUP NUMBER 1',
                            'member_count': 3,
                        }
                    ]
                })
            if params.get('name__icontains') == ['GROUP']:
                return Response({
                    'count': 2,
                    'results': [
                        {
                            'id': 99,
                            'url': 'https://muzillians.fake/en-US/group/99/',
                            'name': 'GROUP NUMBER 1',
                            'member_count': 3,
                        },
                        {
                            'id': 88,
                            'url': 'https://muzillians.fake/en-US/group/88/',
                            'name': 'GROUP THING',
                            'member_count': 5,
                        }
                    ]
                })
            return Response({
                'count': 0,
                'results': []
            })

        rget.side_effect = mocked_get

        url = reverse('main:curated_groups_autocomplete')
        response = self.client.get(url)
        eq_(response.status_code, 302)  # because you're not logged in
        self._login()

        response = self.client.get(url)
        eq_(response.status_code, 400)
        response = self.client.get(url, {'q': ''})
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        eq_(structure['groups'], [])

        response = self.client.get(url, {'q': 'GROUP NUMBER X'})
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        eq_(structure['groups'], [])

        response = self.client.get(url, {'q': 'GROUP NUMBER 1'})
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        eq_(
            structure['groups'], [
                [
                    'GROUP NUMBER 1',
                    'GROUP NUMBER 1 (3 members)'
                ]
            ]
        )
        response = self.client.get(url, {'q': 'GROUP'})
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        eq_(
            structure['groups'], [
                [
                    'GROUP NUMBER 1',
                    'GROUP NUMBER 1 (3 members)'
                ],
                [
                    'GROUP THING',
                    'GROUP THING (5 members)'
                ],
            ]
        )
