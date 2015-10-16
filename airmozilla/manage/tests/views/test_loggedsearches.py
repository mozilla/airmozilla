from nose.tools import eq_, ok_

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from airmozilla.main.models import Event
from airmozilla.search.models import LoggedSearch
from .base import ManageTestCase


class TestLoggedSearches(ManageTestCase):

    def test_loggedsearches(self):
        LoggedSearch.objects.create(
            term='some thing',
            page=1,
            results=100,
            user=None,
            event_clicked=Event.objects.get(title='Test event')
        )
        user, = User.objects.all()[:1]
        LoggedSearch.objects.create(
            term='some else',
            page=1,
            results=22,
            user=user,
            event_clicked=None
        )

        response = self.client.get(reverse('manage:loggedsearches'))
        eq_(response.status_code, 200)

        ok_('Test event' in response.content)
        url = reverse('search:home') + '?q=some+thing&amp;_nolog'
        ok_(url in response.content)

    def test_loggedsearches_stats(self):
        # Deliberately kept very simply because it'sa superuser-only feature
        # and its use is very minimal.
        response = self.client.get(reverse('manage:loggedsearches_stats'))
        eq_(response.status_code, 200)
