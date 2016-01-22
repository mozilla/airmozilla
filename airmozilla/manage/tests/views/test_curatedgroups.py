import json

from nose.tools import eq_
import mock

from django.core.cache import cache
from django.core.urlresolvers import reverse

from airmozilla.base.tests.test_mozillians import (
    Response,
    GROUPS1,
    GROUPS2
)
from .base import ManageTestCase


class TestCuratedGroups(ManageTestCase):

    def tearDown(self):
        super(TestCuratedGroups, self).tearDown()
        cache.clear()

    @mock.patch('logging.error')
    @mock.patch('requests.get')
    def test_curated_groups_autocomplete(self, rget, rlogging):

        def mocked_get(url, **options):
            if '/v2/groups/' in url and 'page=2' in url:
                return Response(GROUPS2)
            if '/v2/groups/' in url:
                return Response(GROUPS1)
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('manage:curated_groups_autocomplete')
        response = self.client.get(url)
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
