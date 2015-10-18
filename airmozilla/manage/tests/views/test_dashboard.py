import datetime
import json

import mock
from nose.tools import eq_, ok_

from django.utils import timezone
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from airmozilla.main.models import Event
from .base import ManageTestCase


class TestDashboard(ManageTestCase):

    def test_dashboard(self):
        response = self.client.get(reverse('manage:dashboard'))
        eq_(response.status_code, 200)

    @mock.patch('django.utils.timezone.now')
    def test_dashboard_data(self, mocked_now):

        specific_date = datetime.datetime(2014, 10, 25, 1, 2, 3)
        specific_date = specific_date.replace(tzinfo=timezone.utc)
        mocked_now.return_value = specific_date

        def user_counts(response):
            data = json.loads(response.content)
            return [
                x['counts'] for x in data['groups'] if x['name'] == 'New Users'
            ][0]

        # we're logged in as user 'fake'
        # delete the others
        User.objects.exclude(username='fake').delete()
        user, = User.objects.all()

        now = timezone.now()
        # let's pretend this user was created "today"
        user.date_joined = now
        user.save()

        url = reverse('manage:dashboard_data')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        counts = user_counts(response)
        eq_(counts['today'], 1)
        eq_(counts['yesterday'], 0)  # one more than last yesterday
        eq_(counts['this_week'], 1)
        eq_(counts['last_week'], 0)
        eq_(counts['this_month'], 1)
        eq_(counts['last_month'], 0)
        eq_(counts['this_year'], 1)
        eq_(counts['last_year'], 0)
        eq_(counts['ever'], 1)

        user.date_joined -= datetime.timedelta(days=1)
        user.save()
        url = reverse('manage:dashboard_data')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        counts = user_counts(response)
        eq_(counts['today'], 0)
        eq_(counts['yesterday'], 1)  # one more than yesterday
        eq_(counts['this_week'], 1)
        eq_(counts['last_week'], 0)
        eq_(counts['this_month'], 1)
        eq_(counts['last_month'], 0)
        eq_(counts['this_year'], 1)
        eq_(counts['last_year'], 0)
        eq_(counts['ever'], 1)

        user.date_joined -= datetime.timedelta(days=6)
        user.save()
        url = reverse('manage:dashboard_data')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        counts = user_counts(response)
        eq_(counts['today'], 0)
        eq_(counts['yesterday'], 0)
        eq_(counts['this_week'], 0)
        eq_(counts['last_week'], 1)
        eq_(counts['this_month'], 1)
        eq_(counts['last_month'], 0)
        eq_(counts['this_year'], 1)
        eq_(counts['last_year'], 0)
        eq_(counts['ever'], 1)

        month = user.date_joined.month
        while user.date_joined.month == month:
            user.date_joined -= datetime.timedelta(days=1)
        user.save()
        url = reverse('manage:dashboard_data')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        counts = user_counts(response)
        eq_(counts['today'], 0)
        eq_(counts['yesterday'], 0)
        eq_(counts['this_week'], 0)
        eq_(counts['last_week'], 0)
        eq_(counts['this_month'], 0)
        eq_(counts['last_month'], 1)
        eq_(counts['this_year'], 1)
        eq_(counts['last_year'], 0)
        eq_(counts['ever'], 1)

        year = user.date_joined.year
        while user.date_joined.year == year:
            user.date_joined -= datetime.timedelta(days=30)
        user.save()
        url = reverse('manage:dashboard_data')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        counts = user_counts(response)
        eq_(counts['today'], 0)
        eq_(counts['yesterday'], 0)
        eq_(counts['this_week'], 0)
        eq_(counts['last_week'], 0)
        eq_(counts['this_month'], 0)
        eq_(counts['last_month'], 0)
        eq_(counts['this_year'], 0)
        eq_(counts['last_year'], 1)
        eq_(counts['ever'], 1)

    def test_dashboard_data_event_durations(self):

        def event_counts(response):
            data = json.loads(response.content)
            return [
                x['counts'] for x in data['groups']
                if x['name'] == 'Total Event Durations'
            ][0]

        assert Event.objects.all().count() == 1
        event = Event.objects.get(title='Test event')

        # let's pretend it was added today
        now = timezone.now()
        event.start_time = now
        event.duration = 30  # 30 seconds
        event.save()

        url = reverse('manage:dashboard_data')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        counts = event_counts(response)
        eq_(counts['today'], '30s')

        event.duration = 300  # 5 minutes
        event.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        counts = event_counts(response)
        eq_(counts['today'], '5m')

        event.duration = 3600 * 3 + 100  # ~ 3 hours
        event.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        counts = event_counts(response)
        eq_(counts['today'], '3h')

    def test_cache_busting_headers(self):
        # viewing any of the public pages should NOT have it
        response = self.client.get('/')
        eq_(response.status_code, 200)
        ok_('no-store' not in response.get('Cache-Control', ''))

        response = self.client.get(reverse('manage:dashboard'))
        eq_(response.status_code, 200)
        ok_('no-store' in response['Cache-Control'])
