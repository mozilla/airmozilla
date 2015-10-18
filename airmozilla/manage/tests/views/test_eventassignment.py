import datetime

from nose.tools import eq_, ok_

from django.contrib.auth.models import User
from django.utils import timezone

from django.core.urlresolvers import reverse

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

        barcelona = Location.objects.create(name='Barcelona')
        moon = Location.objects.create(name='Moon', is_active=False)

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('<option value="%s">' % barcelona.id in response.content)
        ok_('<option value="%s">' % moon.id not in response.content)
        ok_(event.location.name in response.content)

        bob = User.objects.create(username='bob')
        harry = User.objects.create(username='harry')

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
        now = timezone.now()
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
        event1 = Event.objects.create(
            title='Other title',
            start_time=event.start_time,
        )
        # and add a location to the assignment too
        barcelona = Location.objects.create(name='Barcelona')
        assignment.locations.add(barcelona)

        # we can also see a list of
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Other title' in response.content)
        ok_('Barcelona' in response.content)

        event1.status = Event.STATUS_REMOVED
        event1.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Other title' not in response.content)

    def test_event_assignments_ical_for_assignee(self):
        url = reverse('manage:event_assignments_ical')

        event = Event.objects.get(title='Test event')
        now = timezone.now()
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
        start_time_fmt = event.start_time.strftime('%Y%m%dT%H%M%S')
        ok_(start_time_fmt not in response.content)
        padded_start_time_fmt = (
            event.start_time -
            datetime.timedelta(minutes=30)
        ).strftime('%Y%m%dT%H%M%S')
        ok_(padded_start_time_fmt in response.content)
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

    def test_event_assignments_ical_for_all(self):
        url = reverse('manage:event_assignments_ical')

        event = Event.objects.get(title='Test event')
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        event.start_time = tomorrow
        event.save()
        clarissa = User.objects.create(
            username='clarissa',
            email='csorensen@muzilla.com',
        )
        assignment = EventAssignment.objects.create(event=event)
        assignment.users.add(clarissa)
        jlin = User.objects.create(
            username='jlin',
            email='jlin@muzilla.com'
        )
        assignment.users.add(jlin)
        location = Location.objects.create(
            name='Space'
        )
        assignment.locations.add(location)

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('CALNAME:Airmo for crew assignments')
        ok_(event.title in response.content)
        emails = [clarissa.email, jlin.email]
        line = 'DESCRIPTION:Assigned to: ' + '\\, '.join(emails)
        ok_(line in response.content)
        # The event belongs to "two" locations. That of the event and the
        # extra one on the assignment.
        location_names = [event.location.name, location.name]
        line = 'LOCATION:%s' % '\\, '.join(location_names)
        ok_(line in response.content)
