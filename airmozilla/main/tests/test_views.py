import datetime

from django.test import TestCase
from django.utils.timezone import utc

from funfactory.urlresolvers import reverse
from nose.tools import eq_

from airmozilla.main.models import Event, EventOldSlug, Participant


class TestPages(TestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']

    def setUp(self):
        # Make the fixture event live as of the test.
        event = Event.objects.get(title='Test event')
        event.start_time = datetime.datetime.utcnow().replace(tzinfo=utc)
        event.end_time = event.start_time + datetime.timedelta(hours=1)
        event.save()

    def test_home(self):
        """Index page loads and paginates correctly."""
        response = self.client.get(reverse('main:home'))
        eq_(response.status_code, 200)

        response_empty_page = self.client.get(reverse('main:home',
                                              kwargs={'page': 10000}))
        eq_(response_empty_page.status_code, 200)

    def test_event(self):
        """Event view page loads correctly if the event is public and
           scheduled; request a login otherwise."""
        event = Event.objects.get(title='Test event')
        event_page = reverse('main:event', kwargs={'slug': event.slug})
        response_ok = self.client.get(event_page)
        eq_(response_ok.status_code, 200)
        event.public = False
        event.save()
        response_fail = self.client.get(event_page)
        self.assertRedirects(response_fail, reverse('main:login'))
        event.public = True
        event.status = Event.STATUS_INITIATED
        event.save()
        response_fail = self.client.get(event_page)
        self.assertRedirects(response_fail, reverse('main:login'))

    def test_old_slug(self):
        """An old slug will redirect properly to the current event page."""
        old_event_slug = EventOldSlug.objects.get(slug='test-old-slug')
        response = self.client.get(reverse('main:event',
                        kwargs={'slug': old_event_slug.slug}))
        self.assertRedirects(response, reverse('main:event',
             kwargs={'slug': old_event_slug.event.slug}))

    def test_participant(self):
        """Cleared participant responds successfully; else request a login."""
        participant = Participant.objects.get(name='Tim Mickel')
        participant_page = reverse('main:participant',
                                   kwargs={'slug': participant.slug})
        response_ok = self.client.get(participant_page)
        eq_(response_ok.status_code, 200)
        participant.cleared = Participant.CLEARED_NO
        participant.save()
        response_fail = self.client.get(participant_page)
        self.assertRedirects(response_fail, reverse('main:login'))
