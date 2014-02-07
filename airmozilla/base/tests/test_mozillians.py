import json
import random

from django.conf import settings
from django.test import TestCase
from django.core.cache import cache

import mock
from nose.tools import ok_, eq_

from airmozilla.base import mozillians


VOUCHED_FOR = """
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
      "allows_community_sites": true,
      "full_name": "Peter Bengtsson"
    }
  ]
}
"""

NOT_VOUCHED_FOR = """
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
      "website": "http://www.peterbe.com/",
      "bio": "",
      "resource_uri": "/api/v1/users/2430/",
      "last_updated": "2012-11-06T15:37:35",
      "groups": [
        "no beard"
      ],
      "city": "<style>p{font-style:italic}</style>",
      "skills": [],
      "country": "Heard Island and McDonald Islands",
      "region": "Drunk",
      "id": "2430",
      "languages": [],
      "allows_mozilla_sites": true,
      "photo": "http://www.gravatar.com/avatar/23c6d359b6f7af3d3f91ca9e17...",
      "is_vouched": false,
      "email": "tmickel@mit.edu",
      "ircname": "",
      "allows_community_sites": true,
      "full_name": null
    }
  ]
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


IN_GROUPS = """
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
      "photo": "",
      "date_mozillian": null,
      "accounts": [],
      "full_name": "Peter Bengtsson",
      "timezone": "",
      "id": "14321",
      "city": "",
      "vouched_by": 8045,
      "date_vouched": "2014-02-07T15:07:31",
      "languages": [],
      "allows_mozilla_sites": true,
      "email": "peterbe@gmail.com",
      "username": "mail_peterbe",
      "bio": "",
      "groups": [
        "winners",
        "swedes"
      ],
      "allows_community_sites": true,
      "skills": [],
      "country": "af",
      "region": "",
      "url": "https://mozillians.allizom.org/u/mail_peterbe/",
      "is_vouched": true,
      "ircname": "",
      "resource_uri": "/api/v1/users/14321/"
    }
  ]
}
"""


def _random_groups(n):
    all = []
    while len(all) < n:
        templ = """
        {
          "url": "https://mozillians.allizom.org/group/group-%(id)s/",
          "resource_uri": "/api/v1/groups/%(id)s/",
          "number_of_members": %(members)s,
          "id": "%(id)s",
          "name": "group %(id)s"
        }
        """
        context = {
            'id': random.randint(0, 10000),
            'members': random.randint(1, 25)
        }
        all.append((templ % context).strip())
    return all


GROUPS1 = """
{
  "meta": {
    "previous": null,
    "total_count": 750,
    "offset": 0,
    "limit": 500,
    "next": "/api/v1/groups/?limit=500&offset=5&order_by=name"
  },
  "objects": [
    {
      "url": "https://mozillians.allizom.org/group/group-number-1/",
      "resource_uri": "/api/v1/groups/number-1/",
      "number_of_members": 3,
      "id": "12189",
      "name": "GROUP NUMBER 1"
    },
    %s
  ]
}
""" % ',\n'.join(_random_groups(499))

GROUPS2 = """
{
  "meta": {
    "previous": null,
    "total_count": 750,
    "offset": 500,
    "limit": 500,
    "next": "/api/v1/groups/?limit=500&app_name=xxx&offset=5&order_by=name"
  },
  "objects": [
    {
      "url": "https://mozillians.allizom.org/group/group-number-2/",
      "resource_uri": "/api/v1/groups/number-2/",
      "number_of_members": 3,
      "id": "12189",
      "name": "GROUP NUMBER 2"
    },
    %s
  ]
}
""" % ',\n'.join(_random_groups(249))

assert json.loads(VOUCHED_FOR)
assert json.loads(NOT_VOUCHED_FOR)
assert json.loads(NO_VOUCHED_FOR)
assert json.loads(IN_GROUPS)


class Response(object):
    def __init__(self, content=None, status_code=200):
        self.content = content
        self.status_code = status_code


class TestMozillians(TestCase):

    @mock.patch('logging.error')
    @mock.patch('requests.get')
    def test_is_vouched(self, rget, rlogging):
        def mocked_get(url, **options):
            if 'tmickel' in url:
                return Response(NOT_VOUCHED_FOR)
            if 'peterbe' in url:
                return Response(VOUCHED_FOR)
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
        except mozillians.BadStatusCodeError, msg:
            ok_(settings.MOZILLIANS_API_KEY not in str(msg))

    @mock.patch('logging.error')
    @mock.patch('requests.get')
    def test_is_not_vouched(self, rget, rlogging):
        def mocked_get(url, **options):
            if 'tmickel' in url:
                return Response(NO_VOUCHED_FOR)
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        ok_(not mozillians.is_vouched('tmickel@mit.edu'))

    @mock.patch('logging.error')
    @mock.patch('requests.get')
    def test_fetch_user_name(self, rget, rlogging):
        def mocked_get(url, **options):
            if 'peterbe' in url:
                return Response(VOUCHED_FOR)
            if 'tmickel' in url:
                return Response(NOT_VOUCHED_FOR)
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        result = mozillians.fetch_user_name('peterbe@gmail.com')
        eq_(result, 'Peter Bengtsson')
        result = mozillians.fetch_user_name('tmickel@mit.edu')
        eq_(result, None)

    @mock.patch('logging.error')
    @mock.patch('requests.get')
    def test_in_groups(self, rget, rlogging):

        def mocked_get(url, **options):
            if 'peterbe' in url:
                return Response(IN_GROUPS)
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        ok_(not mozillians.in_groups('peterbe@gmail.com', 'losers'))
        ok_(mozillians.in_groups('peterbe@gmail.com', 'winners'))
        ok_(mozillians.in_groups('peterbe@gmail.com', ['winners', 'losers']))

    @mock.patch('logging.error')
    @mock.patch('requests.get')
    def test_get_all_groups(self, rget, rlogging):
        calls = []

        def mocked_get(url, **options):
            calls.append(url)
            if 'offset=0' in url:
                return Response(GROUPS1)
            if 'offset=500' in url:
                return Response(GROUPS2)
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        all = mozillians.get_all_groups()
        eq_(len(all), 750)
        eq_(all[0]['name'], 'GROUP NUMBER 1')
        eq_(all[500]['name'], 'GROUP NUMBER 2')
        eq_(len(calls), 2)

    @mock.patch('logging.error')
    @mock.patch('requests.get')
    def test_get_all_groups_cached(self, rget, rlogging):
        cache.clear()
        calls = []

        def mocked_get(url, **options):
            calls.append(url)
            if 'offset=0' in url:
                return Response(GROUPS1)
            if 'offset=500' in url:
                return Response(GROUPS2)
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        all = mozillians.get_all_groups_cached()
        eq_(len(all), 750)
        eq_(len(calls), 2)

        # a second time
        all = mozillians.get_all_groups_cached()
        eq_(len(all), 750)
        eq_(len(calls), 2)
