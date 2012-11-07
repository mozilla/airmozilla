import json

from django.conf import settings
from django.test import TestCase

from funfactory.urlresolvers import reverse

import mock
from nose.tools import ok_

from airmozilla.auth.browserid_mock import mock_browserid
from airmozilla.auth import mozillians


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
      "allows_community_sites": true
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
      "allows_community_sites": true
    }
  ]
}
"""

assert json.loads(VOUCHED_FOR)
assert json.loads(NOT_VOUCHED_FOR)


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


class TestViews(TestCase):

    def _login_attempt(self, email, assertion='fakeassertion123'):
        with mock_browserid(email):
            r = self.client.post(reverse('auth:mozilla_browserid_verify'),
                                 {'assertion': assertion})
        return r

    def test_invalid(self):
        """Bad BrowserID form (i.e. no assertion) -> failure."""
        response = self._login_attempt(None, None)
        self.assertRedirects(response,
                             reverse(settings.LOGIN_REDIRECT_URL_FAILURE))

    def test_bad_verification(self):
        """Bad verification -> failure."""
        response = self._login_attempt(None)
        self.assertRedirects(response,
                             reverse(settings.LOGIN_REDIRECT_URL_FAILURE))

    @mock.patch('requests.get')
    def test_nonmozilla(self, rget):
        """Non-Mozilla email -> failure."""
        def mocked_get(url, **options):
            if 'tmickel' in url:
                return Response(NOT_VOUCHED_FOR)
            if 'peterbe' in url:
                return Response(VOUCHED_FOR)
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        response = self._login_attempt('tmickel@mit.edu')
        self.assertRedirects(response,
                             reverse(settings.LOGIN_REDIRECT_URL_FAILURE))

        # now with a non-mozillian that is vouched for
        response = self._login_attempt('peterbe@gmail.com')
        self.assertRedirects(response,
                             reverse(settings.LOGIN_REDIRECT_URL))

    def test_mozilla(self):
        """Mozilla email -> success."""
        # Try the first allowed domain
        response = self._login_attempt('tmickel@' + settings.ALLOWED_BID[0])
        self.assertRedirects(response,
                             reverse(settings.LOGIN_REDIRECT_URL))
