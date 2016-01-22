import json

from django.conf import settings
from django.test import TestCase
from django.core.cache import cache

import mock
from nose.tools import ok_, eq_

from airmozilla.base import mozillians
from airmozilla.base.tests.testbase import Response


VOUCHED_FOR_USERS = """
{
  "count": 1,
  "next": null,
  "results": [
    {
      "username": "peterbe",
      "_url": "https://muzillians.fake/api/v2/users/99999/",
      "is_vouched": true
    }
  ],
  "previous": null
}
"""

NO_USERS = """
{
  "count": 0,
  "next": null,
  "results": [],
  "previous": null
}
"""

VOUCHED_FOR = """
{
  "photo": {
    "300x300": "https://muzillians.fake/media/uplo...1caee0.jpg",
    "150x150": "https://muzillians.fake/media/uplo...5636261.jpg",
    "500x500": "https://muzillians.fake/media/uplo...6465a73.jpg",
    "value": "https://muzillians.fake/media/uploa...71caee0.jpg",
    "privacy": "Public"
  },
  "date_mozillian": {
    "value": null,
    "privacy": "Mozillians"
  },
  "full_name": {
    "value": "Peter Bengtsson",
    "privacy": "Public"
  },
  "title": {
    "value": "",
    "privacy": "Mozillians"
  },
  "external_accounts": [],
  "alternate_emails": [],
  "email": {
    "value": "peterbe@mozilla.com",
    "privacy": "Mozillians"
  },
  "username": "peterbe",
  "is_public": true,
  "url": "https://muzillians.fake/en-US/u/peterbe/",
  "country": {
    "code": "us",
    "value": "United States",
    "privacy": "Public"
  },
  "websites": [
    {
      "website": "http://www.peterbe.com/",
      "privacy": "Public"
    }
  ],
  "_url": "https://muzillians.fake/api/v2/users/441/",
  "story_link": {
    "value": "",
    "privacy": "Mozillians"
  },
  "ircname": {
    "value": "peterbe",
    "privacy": "Public"
  },
  "is_vouched": true
}
"""

NOT_VOUCHED_FOR = """
{
  "photo": {
    "300x300": "https://muzillians.fake/media/uplo...1caee0.jpg",
    "150x150": "https://muzillians.fake/media/uplo...5636261.jpg",
    "500x500": "https://muzillians.fake/media/uplo...6465a73.jpg",
    "value": "https://muzillians.fake/media/uploa...71caee0.jpg",
    "privacy": "Public"
  },
  "date_mozillian": {
    "value": null,
    "privacy": "Mozillians"
  },
  "full_name": {
    "value": "Peter Bengtsson",
    "privacy": "Private"
  },
  "title": {
    "value": "",
    "privacy": "Mozillians"
  },
  "alternate_emails": [],
  "email": {
    "value": "peterbe@mozilla.com",
    "privacy": "Mozillians"
  },
  "username": "tmickel",
  "bio": {
    "html": "<p>Web developer at Mozilla</p>",
    "value": "Web developer at Mozilla",
    "privacy": "Public"
  },
  "is_public": true,
  "url": "https://muzillians.fake/en-US/u/peterbe/",
  "websites": [
    {
      "website": "http://www.peterbe.com/",
      "privacy": "Public"
    }
  ],
  "_url": "https://muzillians.fake/api/v2/users/441/",
  "story_link": {
    "value": "",
    "privacy": "Mozillians"
  },
  "ircname": {
    "value": "peterbe",
    "privacy": "Public"
  },
  "is_vouched": false
}
"""

VOUCHED_FOR_NO_USERNAME = """
{
  "meta": {
    "previous": null,
    "total_count": 1,
    "offset": 0,
    "limit": 20,
    "next": null
  },
  "objects": [
    {
      "website": "",
      "bio": "",
      "resource_uri": "/api/v1/users/2429/",
      "last_updated": "2012-11-06T14:41:47",
      "groups": [
        "ugly tuna"
      ],
      "city": "Casino",
      "skills": [],
      "country": "Albania",
      "region": "Bush",
      "id": "2429",
      "languages": [],
      "allows_mozilla_sites": true,
      "photo": "http://www.gravatar.com/avatar/0409b497734934400822bb33...",
      "is_vouched": true,
      "email": "peterbe@gmail.com",
      "ircname": "",
      "allows_community_sites": true
      }
  ]
}
"""

NOT_VOUCHED_FOR_USERS = """
{
  "count": 1,
  "next": null,
  "results": [
    {
      "username": "tmickel@mit.edu",
      "_url": "https://muzillians.fake/api/v2/users/00000/",
      "is_vouched": false
    }
  ],
  "previous": null
}
"""

NO_VOUCHED_FOR = """
{
  "meta": {
    "previous": null,
    "total_count": 0,
    "offset": 0,
    "limit": 20,
    "next": null
  },
  "objects": []
}
"""


GROUPS1 = """
{
  "count": 3,
  "previous": null,
  "results": [
    {
      "url": "https://muzillians.fake/en-US/group/9090909/",
      "_url": "https://muzillians.fake/api/v2/groups/909090/",
      "id": 12426,
      "member_count": 3,
      "name": "GROUP NUMBER 1"
    },
    {
      "url": "https://muzillians.fake/en-US/group/2009-intern/",
      "_url": "https://muzillians.fake/api/v2/groups/08080808/",
      "id": 196,
      "member_count": 7,
      "name": "GROUP NUMBER 2"
    }
  ],
  "next": "https://muzillians.fake/api/v2/groups/?api-key=xxxkey&page=2"
}
"""

GROUPS2 = """
{
  "count": 3,
  "previous": "https://muzillians.fake/api/v2/groups/?api-key=xxxkey",
  "results": [
    {
      "url": "https://muzillians.fake/en-US/group/2013summitassembly/",
      "_url": "https://muzillians.fake/api/v2/groups/02020202/",
      "id": 2002020,
      "member_count": 53,
      "name": "GROUP NUMBER 3"
    }
  ],
  "next": null
}
"""

assert json.loads(VOUCHED_FOR_USERS)
assert json.loads(VOUCHED_FOR)
assert json.loads(NOT_VOUCHED_FOR_USERS)
assert json.loads(NO_VOUCHED_FOR)
assert json.loads(GROUPS1)
assert json.loads(GROUPS2)


class TestMozillians(TestCase):

    def tearDown(self):
        super(TestMozillians, self).tearDown()
        cache.clear()

    @mock.patch('requests.get')
    def test_is_vouched(self, rget):
        def mocked_get(url, **options):
            if 'tmickel' in url:
                return Response(NOT_VOUCHED_FOR_USERS)
            if 'peterbe' in url:
                return Response(VOUCHED_FOR_USERS)
            if 'trouble' in url:
                return Response('Failed', status_code=500)
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        ok_(not mozillians.is_vouched('tmickel@mit.edu'))
        ok_(mozillians.is_vouched('peterbe@gmail.com'))

        self.assertRaises(
            mozillians.BadStatusCodeError,
            mozillians.is_vouched,
            'trouble@live.com'
        )
        # also check that the API key is scrubbed
        try:
            mozillians.is_vouched('trouble@live.com')
            raise
        except mozillians.BadStatusCodeError as msg:
            ok_(settings.MOZILLIANS_API_KEY not in str(msg))

    @mock.patch('requests.get')
    def test_is_not_vouched(self, rget):
        def mocked_get(url, **options):
            if 'tmickel' in url:
                return Response(NOT_VOUCHED_FOR_USERS)
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        ok_(not mozillians.is_vouched('tmickel@mit.edu'))

    @mock.patch('requests.get')
    def test_fetch_user_name(self, rget):
        def mocked_get(url, **options):
            if '/v2/users/99999' in url:
                return Response(VOUCHED_FOR)
            if '/v2/users/00000' in url:
                return Response(NOT_VOUCHED_FOR)
            if 'peterbe' in url:
                return Response(VOUCHED_FOR_USERS)
            if 'tmickel' in url:
                return Response(NOT_VOUCHED_FOR_USERS)
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        result = mozillians.fetch_user_name('peterbe@gmail.com')
        eq_(result, 'Peter Bengtsson')
        result = mozillians.fetch_user_name('tmickel@mit.edu')
        eq_(result, None)

    @mock.patch('requests.get')
    def test_fetch_user_name_failure(self, rget):
        """if the fetching of a single user barfs it shouldn't reveal
        the API key"""

        def mocked_get(url, **options):
            if 'peterbe' in url:
                return Response(VOUCHED_FOR_USERS)
            return Response('Failed', status_code=500)

        rget.side_effect = mocked_get

        try:
            mozillians.fetch_user('peterbe@gmail.com')
            raise AssertionError("shouldn't happen")
        except mozillians.BadStatusCodeError as msg:
            ok_(settings.MOZILLIANS_API_KEY not in str(msg))
            ok_('xxxscrubbedxxx' in str(msg))

    @mock.patch('requests.get')
    def test_fetch_user_name_no_user_name(self, rget):
        def mocked_get(url, **options):
            if '/v2/users/99999' in url:
                return Response(VOUCHED_FOR_NO_USERNAME)
            if 'peterbe' in url and '/v2/users/' in url:
                return Response(VOUCHED_FOR_USERS)
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        result = mozillians.fetch_user_name('peterbe@gmail.com')
        eq_(result, None)

    @mock.patch('requests.get')
    def test_in_group(self, rget):

        def mocked_get(url, **options):
            if 'peterbe' in url:
                if 'group=losers' in url:
                    return Response(NO_USERS)
                if 'group=winners' in url:
                    return Response(VOUCHED_FOR_USERS)
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        ok_(not mozillians.in_group('peterbe@gmail.com', 'losers'))
        ok_(mozillians.in_group('peterbe@gmail.com', 'winners'))

    @mock.patch('requests.get')
    def test_get_all_groups(self, rget):
        calls = []

        def mocked_get(url, **options):
            calls.append(url)
            if '/v2/groups/' in url and 'page=2' in url:
                return Response(GROUPS2)
            if '/v2/groups/' in url:
                return Response(GROUPS1)
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        all = mozillians.get_all_groups()
        eq_(len(all), 3)
        eq_(all[0]['name'], 'GROUP NUMBER 1')
        eq_(all[1]['name'], 'GROUP NUMBER 2')
        eq_(all[2]['name'], 'GROUP NUMBER 3')
        eq_(len(calls), 2)

    @mock.patch('requests.get')
    def test_get_all_groups_failure(self, rget):

        def mocked_get(url, **options):
            return Response('Failed', status_code=500)

        rget.side_effect = mocked_get

        try:
            mozillians.get_all_groups()
            raise AssertionError("shouldn't happen")
        except mozillians.BadStatusCodeError as msg:
            ok_(settings.MOZILLIANS_API_KEY not in str(msg))
            ok_('xxxscrubbedxxx' in str(msg))

    @mock.patch('requests.get')
    def test_get_all_groups_cached(self, rget):
        cache.clear()
        calls = []

        def mocked_get(url, **options):
            calls.append(url)
            if '/v2/groups/' in url and 'page=2' in url:
                return Response(GROUPS2)
            if '/v2/groups/' in url:
                return Response(GROUPS1)
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        all = mozillians.get_all_groups_cached()
        eq_(len(all), 3)
        eq_(len(calls), 2)

        # a second time
        all = mozillians.get_all_groups_cached()
        eq_(len(all), 3)
        eq_(len(calls), 2)
