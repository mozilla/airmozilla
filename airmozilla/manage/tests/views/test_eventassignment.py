import datetime

from nose.tools import eq_, ok_

from django.contrib.auth.models import User
from django.utils.timezone import utc

from funfactory.urlresolvers import reverse

from airmozilla.main.models import Event, EventAssignment, Location
from .base import ManageTestCase


class TestEventAssignment(ManageTestCase):

    def test_event_assignment(self):
        event = Event.objects.get(title='Test event')
        url = reverse('manage:event_assignment', args=(event.pk,))
        edit_url = reverse('manage:event_edit', args=(event.pk,))
        response = self.client.get(edit_url)
        eq_(response.status_code, 200)
        ok_(url in response.content)

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.location.name in response.content)

        bob = User.objects.create(username='bob')
        harry = User.objects.create(username='harry')
        barcelona = Location.objects.create(name='Barcelona')
        data = {
            'users': [bob.pk, harry.pk],
            'locations': [barcelona.pk]
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)

        assignment = EventAssignment.objects.get(event=event)
        ok_(bob in assignment.users.all())
        ok_(harry in assignment.users.all())
        ok_(barcelona in assignment.locations.all())

    def test_event_assignments(self):
        url = reverse('manage:event_assignments')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # set up an assignment for a user
        event = Event.objects.get(title='Test event')
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        tomorrow = now + datetime.timedelta(days=1)
        event.start_time = tomorrow
        event.save()
        clarissa = User.objects.create(
            username='clarissa',
            email='csorensen@muzilla.com',
        )
        assignment = EventAssignment.objects.create(event=event)
        assignment.users.add(clarissa)

        assert event in Event.objects.upcoming()

        feed_url = reverse('manage:event_assignments_ical')
        feed_url += '?assignee=%s' % clarissa.email

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(feed_url in response.content)

        # add another, also upcoming, event and make sure it's
        # working for events that have no assignments too
        Event.objects.create(
            title='Other title',
            start_time=event.start_time
        )
        # and add a location to the assignment too
        barcelona = Location.objects.create(name='Barcelona')
        assignment.locations.add(barcelona)

        # we can also see a list of
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Other title' in response.content)
        ok_('Barcelona' in response.content)

    def test_event_assignments_ical(self):
        url = reverse('manage:event_assignments_ical')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        event = Event.objects.get(title='Test event')
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        tomorrow = now + datetime.timedelta(days=1)
        event.start_time = tomorrow
        event.save()
        clarissa = User.objects.create(
            username='clarissa',
            email='csorensen@muzilla.com',
        )
        assignment = EventAssignment.objects.create(event=event)
        assignment.users.add(clarissa)

        response = self.client.get(url + '?assignee=%s' % clarissa.email)
        eq_(response.status_code, 200)
        ok_('CALNAME:Airmo for %s' % clarissa.email)
        ok_(event.title in response.content)
        ok_('text/calendar' in response['Content-Type'])
        eq_(response['Access-Control-Allow-Origin'], '*')
        ok_(
            'AirMozillaEventAssignments.ics'
            in response['Content-Disposition']
        )

        response = self.client.get(url + '?assignee=some@one.com')
        eq_(response.status_code, 404)

        # check that the headers still work if you cache things
        old_title = event.title
        event.title = 'New Different Title'
        event.save()

        response = self.client.get(url + '?assignee=%s' % clarissa.email)
        eq_(response.status_code, 200)
        ok_(event.title not in response.content)
        ok_(old_title in response.content)
        eq_(response['Access-Control-Allow-Origin'], '*')
        ok_(
            'AirMozillaEventAssignments.ics'
            in response['Content-Disposition']
        )
