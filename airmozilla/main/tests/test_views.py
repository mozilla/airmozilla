import os
import datetime
import httplib
import json
import uuid
import urllib2
import urllib
import re
import time

from django.contrib.flatpages.models import FlatPage
from django.contrib.auth.models import Group, User, AnonymousUser, Permission
from django.contrib.sites.models import Site
from django.utils.timezone import utc
from django.conf import settings
from django.core.cache import cache
from django.core.files import File

from funfactory.urlresolvers import reverse
from nose.tools import eq_, ok_
import mock
import pyquery

from airmozilla.main.models import (
    Approval,
    Event,
    EventOldSlug,
    Participant,
    Tag,
    UserProfile,
    Channel,
    Location,
    Template,
    EventHitStats,
    CuratedGroup,
    EventRevision,
    RecruitmentMessage,
    Picture
)
from airmozilla.base.tests.test_mozillians import (
    Response,
    GROUPS1,
    GROUPS2,
    VOUCHED_FOR
)
from airmozilla.base.tests.testbase import DjangoTestCase


class TestPages(DjangoTestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']
    main_image = 'airmozilla/manage/tests/firefox.png'

    def setUp(self):
        super(TestPages, self).setUp()
        # Make the fixture event live as of the test.
        event = Event.objects.get(title='Test event')
        event.start_time = datetime.datetime.utcnow().replace(tzinfo=utc)
        event.archive_time = None
        event.save()

        self.main_channel = Channel.objects.get(
            slug=settings.DEFAULT_CHANNEL_SLUG
        )

    def _calendar_url(self, privacy, location=None):
        url = reverse('main:calendar_ical', args=(privacy,))
        if location:
            if isinstance(location, int):
                url += '?location=%s' % location
            else:
                if not isinstance(location, int) and 'name' in location:
                    location = location.name
                url += '?location=%s' % urllib.quote_plus(location)
        return url

    def test_contribute_json(self):
        response = self.client.get('/contribute.json')
        eq_(response.status_code, 200)
        # should be valid JSON
        ok_(json.loads(response.content))
        eq_(response['Content-Type'], 'application/json')

    def test_is_contributor(self):
        from airmozilla.main.views import is_contributor
        anonymous = AnonymousUser()
        ok_(not is_contributor(anonymous))

        employee_wo_profile = User.objects.create_user(
            'worker', 'worker@mozilla.com', 'secret'
        )
        ok_(not is_contributor(employee_wo_profile))
        employee_w_profile = User.objects.create_user(
            'worker2', 'worker2@mozilla.com', 'secret'
        )
        assert not UserProfile.objects.filter(user=employee_wo_profile)
        up = UserProfile.objects.create(
            user=employee_w_profile,
            contributor=False
        )
        ok_(not is_contributor(employee_w_profile))
        up.contributor = True
        up.save()
        # re-fetch to avoid internal django cache on profile fetching
        employee_w_profile = User.objects.get(pk=employee_w_profile.pk)
        ok_(is_contributor(employee_w_profile))

        contributor = User.objects.create_user(
            'nigel', 'nigel@live.com', 'secret'
        )
        UserProfile.objects.create(
            user=contributor,
            contributor=True
        )
        ok_(is_contributor(contributor))

    def test_is_employee(self):
        from airmozilla.main.views import is_employee
        user = User.objects.create(username='a', email='some@crack.com')
        ok_(not is_employee(user))

        from random import choice
        user = User.objects.create(
            username='b',
            email='foo@' + choice(settings.ALLOWED_BID)
        )
        ok_(is_employee(user))

    def test_can_view_event(self):
        event = Event.objects.get(title='Test event')
        assert event.privacy == Event.PRIVACY_PUBLIC  # default

        anonymous = AnonymousUser()
        employee_wo_profile = User.objects.create_user(
            'worker', 'worker@mozilla.com', 'secret'
        )
        employee_w_profile = User.objects.create_user(
            'worker2', 'worker2@mozilla.com', 'secret'
        )
        assert not UserProfile.objects.filter(user=employee_wo_profile)
        UserProfile.objects.create(
            user=employee_w_profile,
            contributor=False
        )
        contributor = User.objects.create_user(
            'nigel', 'nigel@live.com', 'secret'
        )
        UserProfile.objects.create(
            user=contributor,
            contributor=True
        )

        from airmozilla.main.views import can_view_event, is_contributor
        ok_(can_view_event(event, anonymous))
        assert not is_contributor(anonymous)

        ok_(can_view_event(event, contributor))
        assert is_contributor(contributor)

        ok_(can_view_event(event, employee_wo_profile))
        assert not is_contributor(employee_wo_profile)

        ok_(can_view_event(event, employee_w_profile))
        assert not is_contributor(employee_w_profile)

        event.privacy = Event.PRIVACY_COMPANY
        event.save()
        ok_(not can_view_event(event, anonymous))
        ok_(not can_view_event(event, contributor))
        ok_(can_view_event(event, employee_wo_profile))
        ok_(can_view_event(event, employee_w_profile))

        event.privacy = Event.PRIVACY_CONTRIBUTORS
        event.save()
        ok_(not can_view_event(event, anonymous))
        ok_(can_view_event(event, contributor))
        ok_(can_view_event(event, employee_wo_profile))
        ok_(can_view_event(event, employee_w_profile))

    def test_view_event_with_pin(self):
        cache.clear()
        event = Event.objects.get(title='Test event')
        event.privacy = Event.PRIVACY_CONTRIBUTORS
        event.description = "My Event Description"
        event.pin = '12345'
        event.save()
        url = reverse('main:event', args=(event.slug,))

        response = self.client.get(url)
        self.assertRedirects(
            response,
            reverse('main:login') + '?next=%s' % url
        )

        User.objects.create_user(
            'mary', 'mary@mozilla.com', 'secret'
        )
        assert self.client.login(username='mary', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.description in response.content)

        contributor = User.objects.create_user(
            'nigel', 'nigel@live.com', 'secret'
        )
        UserProfile.objects.create(
            user=contributor,
            contributor=True
        )
        assert self.client.login(username='nigel', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.description not in response.content)
        ok_('id="id_pin"' in response.content)

        # attempt a pin
        response = self.client.post(url, {'pin': '1'})
        eq_(response.status_code, 200)
        ok_(event.description not in response.content)
        ok_('id="id_pin"' in response.content)
        ok_('Incorrect pin' in response.content)

        response = self.client.post(url, {'pin': ' 12345 '})
        eq_(response.status_code, 302)
        self.assertRedirects(response, url)

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.description in response.content)
        ok_('id="id_pin"' not in response.content)

    def test_view_public_event_with_pin(self):
        event = Event.objects.get(title='Test event')
        event.privacy = Event.PRIVACY_PUBLIC
        event.description = "My Event Description"
        event.pin = '12345'
        event.save()
        url = reverse('main:event', args=(event.slug,))

        response = self.client.get(url)
        eq_(response.status_code, 200)
        # expect the pin input to be there
        ok_('id="id_pin"' in response.content)
        response = self.client.post(url, {'pin': ' 12345 '})
        eq_(response.status_code, 302)
        self.assertRedirects(response, url)

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.description in response.content)
        ok_('id="id_pin"' not in response.content)

    def test_view_private_events_with_notices(self):
        # for https://bugzilla.mozilla.org/show_bug.cgi?id=821458
        event = Event.objects.get(title='Test event')
        assert event.privacy == Event.PRIVACY_PUBLIC  # default
        event.privacy = Event.PRIVACY_CONTRIBUTORS
        event.save()

        url = reverse('main:event', args=(event.slug,))
        response = self.client.get(url)
        self.assertRedirects(
            response,
            reverse('main:login') + '?next=%s' % url
        )

        contributor = User.objects.create_user(
            'nigel', 'nigel@live.com', 'secret'
        )
        UserProfile.objects.create(
            user=contributor,
            contributor=True
        )

        assert self.client.login(username='nigel', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(
            'This event is available only to Mozilla volunteers and staff'
            in response.content
        )

        event.privacy = Event.PRIVACY_COMPANY
        event.save()

        response = self.client.get(url)
        permission_denied_url = reverse(
            'main:permission_denied',
            args=(event.slug,)
        )
        self.assertRedirects(response, permission_denied_url)
        # actually go there
        response = self.client.get(permission_denied_url)
        eq_(response.status_code, 200)
        ok_('This event is only for Mozilla staff')

        User.objects.create_user(
            'worker', 'worker@mozilla.com', 'secret'
        )
        assert self.client.login(username='worker', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(
            'This event is available only to Mozilla staff'
            in response.content
        )

    def test_home(self):
        """Index page loads and paginates correctly."""
        response = self.client.get(reverse('main:home'))
        eq_(response.status_code, 200)

        response_empty_page = self.client.get(reverse('main:home',
                                              kwargs={'page': 10000}))
        eq_(response_empty_page.status_code, 200)

    def test_event(self):
        """Event view page loads correctly if the event is public and
           scheduled and approved; request a login otherwise."""
        event = Event.objects.get(title='Test event')
        group = Group.objects.get()
        approval = Approval(event=event, group=group)
        approval.save()
        event_page = reverse('main:event', kwargs={'slug': event.slug})
        response_fail_approval = self.client.get(event_page)
        eq_(response_fail_approval.status_code, 200)
        ok_('not approved' in response_fail_approval.content)
        approval.approved = True
        approval.processed = True
        approval.save()
        response_ok = self.client.get(event_page)
        eq_(response_ok.status_code, 200)
        event.privacy = Event.PRIVACY_COMPANY
        event.save()
        response_fail = self.client.get(event_page)
        self.assertRedirects(
            response_fail,
            reverse('main:login') + '?next=%s' % event_page
        )
        event.privacy = Event.PRIVACY_CONTRIBUTORS
        event.save()
        response_fail = self.client.get(event_page)
        self.assertRedirects(
            response_fail,
            reverse('main:login') + '?next=%s' % event_page
        )
        event.privacy = Event.PRIVACY_PUBLIC
        event.status = Event.STATUS_INITIATED
        event.save()
        response_fail = self.client.get(event_page)
        eq_(response_fail.status_code, 200)
        ok_('This event is no longer available.' in response_fail.content)

        self.client.logout()
        event.privacy = Event.PRIVACY_COMPANY
        event.status = Event.STATUS_SCHEDULED
        event.save()
        response_fail = self.client.get(event_page)
        self.assertRedirects(
            response_fail,
            reverse('main:login') + '?next=%s' % event_page
        )

        nigel = User.objects.create_user('nigel', 'n@live.in', 'secret')
        UserProfile.objects.create(user=nigel, contributor=True)
        assert self.client.login(username='nigel', password='secret')

        response_fail = self.client.get(event_page)
        self.assertRedirects(
            response_fail,
            reverse('main:permission_denied', args=(event.slug,))
        )

        event.privacy = Event.PRIVACY_CONTRIBUTORS
        event.save()
        response_ok = self.client.get(event_page)
        eq_(response_ok.status_code, 200)

    def test_event_with_vidly_download_links(self):
        event = Event.objects.get(title='Test event')
        vidly = Template.objects.create(
            name="Vid.ly HD",
            content='<iframe src="{{ tag }}"></iframe>'
        )
        event.template = vidly
        event.template_environment = {'tag': 'abc123'}
        event.save()
        url = reverse('main:event', kwargs={'slug': event.slug})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        assert event.privacy == Event.PRIVACY_PUBLIC

        ok_(
            'https://vid.ly/abc123?content=video&amp;format=webm'
            in response.content
        )
        ok_(
            'https://vid.ly/abc123?content=video&amp;format=mp4'
            in response.content
        )

    def test_private_event_redirect(self):
        event = Event.objects.get(title='Test event')
        event.privacy = Event.PRIVACY_COMPANY
        event.save()
        url = reverse('main:event', args=(event.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:login') + '?next=%s' % url
        )

    def test_event_upcoming(self):
        """View an upcoming event and it should show the local time"""
        event = Event.objects.get(title='Test event')
        date = datetime.datetime(2099, 1, 1, 18, 0, 0).replace(tzinfo=utc)
        event.start_time = date
        event.save()
        group = Group.objects.get()
        approval = Approval(event=event, group=group)
        approval.approved = True
        approval.save()
        event_page = reverse('main:event', kwargs={'slug': event.slug})
        response = self.client.get(event_page)
        eq_(response.status_code, 200)
        assert event.location
        ok_(event.location.name in response.content)
        # 18:00 in UTC on that 1st Jan 2099 is 10AM in Pacific time
        assert event.location.timezone == 'US/Pacific'
        ok_('10:00AM' in response.content)

    def test_event_in_cyberspace(self):
        event = Event.objects.get(title='Test event')
        assert 'Cyberspace' not in event.location.name
        event_page = reverse('main:event', kwargs={'slug': event.slug})
        response = self.client.get(event_page)
        eq_(response.status_code, 200)
        ok_(event.location.name in response.content)

        cyberspace, __ = Location.objects.get_or_create(
            name='Cyberspace',
            timezone='UTC'
        )
        event.location = cyberspace
        event.save()
        response = self.client.get(event_page)
        eq_(response.status_code, 200)
        ok_(event.location.name not in response.content)

        cyberspace_pacific, __ = Location.objects.get_or_create(
            name='Cyberspace Pacific',
            timezone='US/Pacific'
        )
        event.location = cyberspace_pacific
        event.save()
        response = self.client.get(event_page)
        eq_(response.status_code, 200)
        ok_(event.location.name not in response.content)

    def test_old_slug(self):
        """An old slug will redirect properly to the current event page."""
        old_event_slug = EventOldSlug.objects.get(slug='test-old-slug')
        response = self.client.get(
            reverse('main:event', kwargs={'slug': old_event_slug.slug})
        )
        self.assertRedirects(
            response,
            reverse('main:event', kwargs={'slug': old_event_slug.event.slug})
        )

    def test_participant(self):
        """Participant pages always respond successfully."""
        participant = Participant.objects.get(name='Tim Mickel')
        participant_page = reverse('main:participant',
                                   kwargs={'slug': participant.slug})
        response_ok = self.client.get(participant_page)
        eq_(response_ok.status_code, 200)
        participant.cleared = Participant.CLEARED_NO
        participant.save()
        response_ok = self.client.get(participant_page)
        eq_(response_ok.status_code, 200)

    def test_participant_clear(self):
        """Visiting a participant clear token page changes the Participant
           status as expected."""
        participant = Participant.objects.get(name='Tim Mickel')
        participant.cleared = Participant.CLEARED_NO
        token = str(uuid.uuid4())
        participant.clear_token = token
        participant.save()
        url = reverse('main:participant_clear', kwargs={'clear_token': token})
        response_ok = self.client.get(url)
        eq_(response_ok.status_code, 200)
        response_changed = self.client.post(url)
        eq_(response_changed.status_code, 200)
        participant = Participant.objects.get(name='Tim Mickel')
        eq_(participant.clear_token, '')
        eq_(participant.cleared, Participant.CLEARED_YES)

    def test_calendar_ical(self):
        url = self._calendar_url('public')
        response_public = self.client.get(url)
        eq_(response_public.status_code, 200)
        eq_(response_public['Access-Control-Allow-Origin'], '*')
        ok_('LOCATION:Mountain View' in response_public.content)
        private_url = self._calendar_url('company')
        response_private = self.client.get(private_url)
        eq_(response_private.status_code, 200)
        # Cache tests
        event_change = Event.objects.get(id=22)
        event_change.title = 'Hello cache clear!'
        event_change.save()
        response_changed = self.client.get(url)
        ok_(response_changed.content != response_public.content)
        ok_('cache clear!' in response_changed.content)

    def test_calendar_dtstart(self):
        """Test the behavior of the `DTSTART` value in the iCal feed."""
        event = Event.objects.get(title='Test event')
        dtstart = event.start_time - datetime.timedelta(minutes=30)
        dtstart = dtstart.strftime("DTSTART:%Y%m%dT%H%M%SZ")
        url = self._calendar_url('public')
        response_public = self.client.get(url)
        ok_(dtstart in response_public.content)

    def test_calendar_dtend(self):
        """Test the behavior of the `DTEND` value in the iCal feed."""
        event = Event.objects.get(title='Test event')
        dtend = event.start_time + datetime.timedelta(hours=1)
        dtend = dtend.strftime("DTEND:%Y%m%dT%H%M%SZ")
        url = self._calendar_url('public')
        response_public = self.client.get(url)
        ok_(dtend in response_public.content)

    def test_calendar_ical_cors_cached(self):
        url = self._calendar_url('public')
        response_public = self.client.get(url)
        eq_(response_public.status_code, 200)
        eq_(response_public['Access-Control-Allow-Origin'], '*')
        ok_('LOCATION:Mountain View' in response_public.content)

        response_public = self.client.get(url)
        eq_(response_public.status_code, 200)
        eq_(response_public['Access-Control-Allow-Origin'], '*')

    def test_calendar_with_location(self):
        london = Location.objects.create(
            name='London',
            timezone='Europe/London'
        )
        event1 = Event.objects.get(title='Test event')
        # know your fixtures
        assert event1.location.name == 'Mountain View'

        event2 = Event.objects.create(
            title='Second test event',
            description='Anything',
            start_time=event1.start_time,
            archive_time=event1.archive_time,
            privacy=Event.PRIVACY_PUBLIC,
            status=event1.status,
            placeholder_img=event1.placeholder_img,
            location=london
        )
        event2.channels.add(self.main_channel)
        assert event1.location != event2.location

        url = self._calendar_url('public')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)
        ok_('Second test event' in response.content)

        response = self.client.get(url, {'location': 'bla bla'})
        eq_(response.status_code, 404)

        response = self.client.get(url, {'location': event1.location.name})
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)
        ok_('Second test event' not in response.content)

        response = self.client.get(url, {'location': event2.location.name})
        eq_(response.status_code, 200)
        ok_('Test event' not in response.content)
        ok_('Second test event' in response.content)

        # same can be reached by ID
        response = self.client.get(url, {'location': event1.location.id})
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)
        ok_('Second test event' not in response.content)

    def test_calendars_page(self):
        london = Location.objects.create(
            name='London',
            timezone='Europe/London'
        )
        event1 = Event.objects.get(title='Test event')
        # know your fixtures
        assert event1.location.name == 'Mountain View'

        event2 = Event.objects.create(
            title='Second test event',
            description='Anything',
            start_time=event1.start_time,
            archive_time=event1.archive_time,
            privacy=Event.PRIVACY_PUBLIC,
            status=event1.status,
            placeholder_img=event1.placeholder_img,
            location=london
        )
        event2.channels.add(self.main_channel)
        assert event1.location != event2.location

        url = reverse('main:calendars')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('London' in response.content)
        ok_('Mountain View' in response.content)

        # we can expect three URLs to calendar feeds to be in there
        url_all = self._calendar_url('public')
        url_lon = self._calendar_url('public', london.pk)
        url_mv = self._calendar_url('public', event1.location.pk)
        ok_(url_all in response.content)
        ok_(url_lon in response.content)
        ok_(url_mv in response.content)

        # now, log in as a contributor
        contributor = User.objects.create_user(
            'nigel', 'nigel@live.com', 'secret'
        )
        UserProfile.objects.create(
            user=contributor,
            contributor=True
        )
        assert self.client.login(username='nigel', password='secret')
        url = reverse('main:calendars')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        url_all = self._calendar_url('contributors')
        url_lon = self._calendar_url('contributors', london.pk)
        url_mv = self._calendar_url('contributors', event1.location.pk)
        ok_(url_all in response.content)
        ok_(url_lon in response.content)
        ok_(url_mv in response.content)

        # now log in as an employee
        User.objects.create_user(
            'peterbe', 'peterbe@mozilla.com', 'secret'
        )
        assert self.client.login(username='peterbe', password='secret')
        url = reverse('main:calendars')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        url_all = self._calendar_url('company')
        url_lon = self._calendar_url('company', london.pk)
        url_mv = self._calendar_url('company', event1.location.pk)
        ok_(url_all in response.content)
        ok_(url_lon in response.content)
        ok_(url_mv in response.content)

    def test_calendars_page_locations_disappear(self):
        london = Location.objects.create(
            name='London',
            timezone='Europe/London'
        )
        event1 = Event.objects.get(title='Test event')
        # know your fixtures
        assert event1.location.name == 'Mountain View'

        event2 = Event.objects.create(
            title='Second test event',
            description='Anything',
            start_time=event1.start_time,
            archive_time=event1.archive_time,
            privacy=Event.PRIVACY_PUBLIC,
            status=event1.status,
            placeholder_img=event1.placeholder_img,
            location=london
        )
        event2.channels.add(self.main_channel)
        assert event1.location != event2.location

        url = reverse('main:calendars')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('London' in response.content)
        ok_('Mountain View' in response.content)
        # we can expect three URLs to calendar feeds to be in there
        url_all = self._calendar_url('public')
        url_lon = self._calendar_url('public', london.pk)
        url_mv = self._calendar_url('public', event1.location.pk)
        ok_(url_all in response.content)
        ok_(url_lon in response.content)
        ok_(url_mv in response.content)

        # but, suppose the events belonging to MV is far future
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        event1.start_time = now + datetime.timedelta(days=20)
        event1.save()
        # and, suppose the events belong to London is very very old
        event2.start_time = now - datetime.timedelta(days=100)
        event2.archive_time = now - datetime.timedelta(days=99)
        event2.save()
        assert event2 in Event.objects.archived().all()

        url = reverse('main:calendars')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('London' not in response.content)
        ok_('Mountain View' in response.content)
        # we can expect three URLs to calendar feeds to be in there
        ok_(url_all in response.content)
        ok_(url_lon not in response.content)
        ok_(url_mv in response.content)

    def test_calendars_description(self):
        event = Event.objects.get(title='Test event')
        event.description = """
        Check out the <a href="http://example.com">Example</a> page
        and <strong>THIS PAGE</strong> here.

        Lorem Ipsum is simply dummy text of the printing and typesetting
        industry. Lorem Ipsum has been the industry's standard dummy text
        ever since the 1500s, when an unknown printer took a galley of type
        and scrambled it to make a type specimen book.
        If the text is getting really long it will be truncated.
        """.strip()
        event.save()
        response_public = self.client.get(self._calendar_url('public'))
        eq_(response_public.status_code, 200)
        ok_('Check out the Example page' in response_public.content)
        ok_('and THIS PAGE here' in response_public.content)
        ok_('will be truncated' not in response_public.content)

        event.short_description = 'One-liner'
        event.save()
        response_public = self.client.get(self._calendar_url('public'))
        eq_(response_public.status_code, 200)
        ok_('Check out the' not in response_public.content)
        ok_('One-liner' in response_public.content)

    def test_filter_by_tags(self):
        url = reverse('main:home')
        delay = datetime.timedelta(days=1)

        event1 = Event.objects.get(title='Test event')
        event1.status = Event.STATUS_SCHEDULED
        event1.start_time -= delay
        event1.archive_time = event1.start_time
        event1.save()

        eq_(Event.objects.approved().count(), 1)
        eq_(Event.objects.archived().count(), 1)

        event2 = Event.objects.create(
            title='Second test event',
            description='Anything',
            start_time=event1.start_time,
            archive_time=event1.archive_time,
            privacy=Event.PRIVACY_PUBLIC,
            status=event1.status,
            placeholder_img=event1.placeholder_img,
        )
        event2.channels.add(self.main_channel)

        eq_(Event.objects.approved().count(), 2)
        eq_(Event.objects.archived().count(), 2)

        tag1 = Tag.objects.create(name='tag1')
        tag2 = Tag.objects.create(name='tag2')
        tag3 = Tag.objects.create(name='tag3')
        event1.tags.add(tag1)
        event1.tags.add(tag2)
        event2.tags.add(tag2)
        event2.tags.add(tag3)

        # check that both events appear
        response = self.client.get(url)
        ok_('Test event' in response.content)
        ok_('Second test event' in response.content)

        response = self.client.get(url, {'tag': 'tag2'})
        ok_('Test event' in response.content)
        ok_('Second test event' in response.content)

        response = self.client.get(url, {'tag': 'tag1'})
        ok_('Test event' in response.content)
        ok_('Second test event' not in response.content)

        response = self.client.get(url, {'tag': 'tag3'})
        ok_('Test event' not in response.content)
        ok_('Second test event' in response.content)

        response = self.client.get(url, {'tag': ['tag1', 'tag3']})
        ok_('Test event' in response.content)
        ok_('Second test event' in response.content)

        response = self.client.get(url, {'tag': 'Bogus'})
        eq_(response.status_code, 301)

        response = self.client.get(url, {'tag': ['tag1', 'Bogus']})
        eq_(response.status_code, 301)
        # the good tag stays
        ok_('?tag=tag1' in response['Location'])

    def test_filter_by_duplicate_tags(self):
        """this is mainly a fix for a legacy situation where you might
        have accidentally allowed in two equal tags that are only
        different in their case"""
        url = reverse('main:home')
        delay = datetime.timedelta(days=1)

        event1 = Event.objects.get(title='Test event')
        event1.status = Event.STATUS_SCHEDULED
        event1.start_time -= delay
        event1.archive_time = event1.start_time
        event1.save()

        eq_(Event.objects.approved().count(), 1)
        eq_(Event.objects.archived().count(), 1)

        event2 = Event.objects.create(
            title='Second test event',
            description='Anything',
            start_time=event1.start_time,
            archive_time=event1.archive_time,
            privacy=Event.PRIVACY_PUBLIC,
            status=event1.status,
            placeholder_img=event1.placeholder_img,
        )
        event2.channels.add(self.main_channel)

        eq_(Event.objects.approved().count(), 2)
        eq_(Event.objects.archived().count(), 2)

        tag1a = Tag.objects.create(name='tag1')
        tag1b = Tag.objects.create(name='TAG1')
        event1.tags.add(tag1a)
        event2.tags.add(tag1b)

        # check that both events appear
        response = self.client.get(url)
        ok_('Test event' in response.content)
        ok_('Second test event' in response.content)

        response = self.client.get(url, {'tag': 'TaG1'})
        ok_('Test event' in response.content)
        ok_('Second test event' in response.content)

    def test_feed(self):
        delay = datetime.timedelta(days=1)

        event1 = Event.objects.get(title='Test event')
        event1.status = Event.STATUS_SCHEDULED
        event1.start_time -= delay
        event1.archive_time = event1.start_time
        event1.save()
        eq_(Event.objects.approved().count(), 1)
        eq_(Event.objects.archived().count(), 1)

        event = Event.objects.create(
            title='Second test event',
            description='Anything',
            start_time=event1.start_time,
            archive_time=event1.archive_time,
            privacy=Event.PRIVACY_COMPANY,  # Note!
            status=event1.status,
            placeholder_img=event1.placeholder_img,
        )
        event.channels.add(self.main_channel)

        eq_(Event.objects.approved().count(), 2)
        eq_(Event.objects.archived().count(), 2)

        url = reverse('main:feed', args=('public',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)
        ok_('Second test event' not in response.content)

        url = reverse('main:feed')  # public feed
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)
        ok_('Second test event' not in response.content)

        url = reverse('main:feed', args=('company',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)
        ok_('Second test event' in response.content)

    def test_feed_with_webm_format(self):
        delay = datetime.timedelta(days=1)

        event1 = Event.objects.get(title='Test event')
        event1.status = Event.STATUS_SCHEDULED
        event1.start_time -= delay
        event1.archive_time = event1.start_time
        vidly_template = Template.objects.create(
            name='Vid.ly Something',
            content='<script>'
        )
        event1.template = vidly_template
        event1.template_environment = {'tag': 'abc123'}
        event1.save()
        eq_(Event.objects.approved().count(), 1)
        eq_(Event.objects.archived().count(), 1)

        url = reverse('main:feed_format_type', args=('public', 'webm'))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(
            '<link>https://vid.ly/abc123?content=video&amp;format=webm</link>'
            in response.content
        )

    def test_feed_cache(self):
        delay = datetime.timedelta(days=1)

        event = Event.objects.get(title='Test event')
        event.start_time -= delay
        event.archive_time = event.start_time
        event.save()

        url = reverse('main:feed')
        eq_(Event.objects.approved().count(), 1)
        eq_(Event.objects.archived().count(), 1)
        response = self.client.get(url)
        ok_('Test event' in response.content)

        event.title = 'Totally different'
        event.save()

        response = self.client.get(url)
        ok_('Test event' in response.content)
        ok_('Totally different' not in response.content)

    def test_private_feeds_by_channel(self):
        channel = Channel.objects.create(
            name='Culture and Context',
            slug='culture-and-context',
        )
        delay = datetime.timedelta(days=1)

        event1 = Event.objects.get(title='Test event')
        event1.status = Event.STATUS_SCHEDULED
        event1.start_time -= delay
        event1.archive_time = event1.start_time
        event1.save()
        event1.channels.clear()
        event1.channels.add(channel)

        eq_(Event.objects.approved().count(), 1)
        eq_(Event.objects.archived().count(), 1)

        event = Event.objects.create(
            title='Second test event',
            description='Anything',
            start_time=event1.start_time,
            archive_time=event1.archive_time,
            privacy=Event.PRIVACY_COMPANY,  # Note!
            status=event1.status,
            placeholder_img=event1.placeholder_img,
        )
        event.channels.add(channel)

        eq_(Event.objects.approved().count(), 2)
        eq_(Event.objects.archived().count(), 2)
        eq_(Event.objects.filter(channels=channel).count(), 2)

        url = reverse(
            'main:channel_feed',
            args=('culture-and-context', 'public')
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)
        ok_('Second test event' not in response.content)

        # public feed
        url = reverse(
            'main:channel_feed_default',
            args=('culture-and-context',)
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)
        ok_('Second test event' not in response.content)

        url = reverse(
            'main:channel_feed',
            args=('culture-and-context', 'company')
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)
        ok_('Second test event' in response.content)

    def test_feeds_by_channel_with_webm_format(self):
        channel = Channel.objects.create(
            name='Culture and Context',
            slug='culture-and-context',
        )
        delay = datetime.timedelta(days=1)

        event1 = Event.objects.get(title='Test event')
        event1.status = Event.STATUS_SCHEDULED
        event1.start_time -= delay
        event1.archive_time = event1.start_time
        vidly_template = Template.objects.create(
            name='Vid.ly Something',
            content='<script>'
        )
        event1.template = vidly_template
        event1.template_environment = {'tag': 'abc123'}
        event1.save()
        event1.channels.clear()
        event1.channels.add(channel)

        event = Event.objects.create(
            title='Second test event',
            description='Anything',
            start_time=event1.start_time,
            archive_time=event1.archive_time,
            privacy=Event.PRIVACY_PUBLIC,
            status=event1.status,
            placeholder_img=event1.placeholder_img,
        )

        event.channels.add(channel)

        eq_(Event.objects.approved().count(), 2)
        eq_(Event.objects.archived().count(), 2)
        eq_(Event.objects.filter(channels=channel).count(), 2)

        url = reverse(
            'main:channel_feed_format_type',
            args=('culture-and-context', 'public', 'webm')
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        assert 'Second test event' in response.content
        ok_(
            '<link>https://vid.ly/abc123?content=video&amp;format=webm</link>'
            in response.content
        )

    def test_rendering_additional_links(self):
        event = Event.objects.get(title='Test event')
        event.additional_links = 'Google'
        event.save()

        url = reverse('main:event', args=(event.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Google' in response.content)

        event.additional_links = """
        Google http://google.com
        """.strip()
        event.save()
        response = self.client.get(url)
        ok_(
            'Google <a href="http://google.com">http://google.com</a>' in
            response.content
        )

        event.additional_links = """
        Google http://google.com\nYahii http://yahii.com
        """.strip()
        event.save()
        response = self.client.get(url)

        ok_(
            'Google <a href="http://google.com">http://google.com</a><br>'
            'Yahii <a href="http://yahii.com">http://yahii.com</a>'
            in response.content
        )

    @mock.patch('airmozilla.manage.vidly.urllib2.urlopen')
    def test_event_with_vidly_token_urlerror(self, p_urlopen):
        # based on https://bugzilla.mozilla.org/show_bug.cgi?id=811476
        event = Event.objects.get(title='Test event')

        # first we need a template that uses `vidly_tokenize()`
        template = event.template
        template.content = """
        {% set token = vidly_tokenize(tag, 90) %}
        <iframe src="http://s.vid.ly/embeded.html?
        link={{ tag }}{% if token %}&token={{ token }}{% endif %}"></iframe>
        """
        template.save()
        event.template_environment = "tag=abc123"
        event.save()

        p_urlopen.side_effect = urllib2.URLError('ANGER!')

        url = reverse('main:event', args=(event.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Temporary network error' in response.content)

    @mock.patch('airmozilla.manage.vidly.urllib2.urlopen')
    def test_event_with_vidly_token_badstatusline(self, p_urlopen):
        # based on https://bugzilla.mozilla.org/show_bug.cgi?id=842588
        event = Event.objects.get(title='Test event')

        # first we need a template that uses `vidly_tokenize()`
        template = event.template
        template.content = """
        {% set token = vidly_tokenize(tag, 90) %}
        <iframe src="http://s.vid.ly/embeded.html?
        link={{ tag }}{% if token %}&token={{ token }}{% endif %}"></iframe>
        """
        template.save()
        event.template_environment = "tag=abc123"
        event.save()

        p_urlopen.side_effect = httplib.BadStatusLine('TroubleX')

        url = reverse('main:event', args=(event.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Temporary network error' in response.content)
        ok_('TroubleX' not in response.content)

    def test_404_page_with_side_events(self):
        """404 pages should work when there's stuff in the side bar"""
        event1 = Event.objects.get(title='Test event')
        now = datetime.datetime.utcnow().replace(tzinfo=utc)

        event = Event.objects.create(
            title='Second test event',
            description='Anything',
            start_time=now + datetime.timedelta(days=10),
            privacy=Event.PRIVACY_PUBLIC,
            status=event1.status,
            placeholder_img=event1.placeholder_img,
        )
        event.channels.add(self.main_channel)

        event = Event.objects.create(
            title='Third test event',
            description='Anything',
            start_time=now + datetime.timedelta(days=20),
            privacy=Event.PRIVACY_COMPANY,
            status=event1.status,
            placeholder_img=event1.placeholder_img,
        )
        event.channels.add(self.main_channel)

        response = self.client.get(reverse('main:home'))
        eq_(response.status_code, 200)
        ok_('Second test event' in response.content)
        ok_('Third test event' not in response.content)

        response = self.client.get('/doesnotexist/')
        eq_(response.status_code, 404)
        ok_('Second test event' in response.content)
        ok_('Third test event' not in response.content)

        User.objects.create_user(
            'worker', 'worker@mozilla.com', 'secret'
        )
        assert self.client.login(username='worker', password='secret')
        response = self.client.get(reverse('main:home'))
        eq_(response.status_code, 200)
        ok_('Second test event' in response.content)
        ok_('Third test event' in response.content)

        response = self.client.get('/doesnotexist/')
        eq_(response.status_code, 404)
        ok_('Second test event' in response.content)
        ok_('Third test event' in response.content)

    def test_render_favicon(self):
        # because /favicon.ico isn't necessarily set up in Apache
        response = self.client.get('/favicon.ico')
        eq_(response.status_code, 200)
        ok_content_types = ('image/vnd.microsoft.icon', 'image/x-icon')
        # it's potentially differnet content type depending on how different
        # servers guess .ico files
        # On my OSX it's image/x-icon
        ok_(response['Content-Type'] in ok_content_types)

    def test_channels_page(self):
        channel = Channel.objects.create(
            name='Culture & Context',
            slug='culture-and-context',
        )
        Channel.objects.create(
            name='Sub-Culture & Subtle-Context',
            slug='sub-culture-and-sub-context',
            parent=channel
        )

        # create an archived event that can belong to this channel
        event1 = Event.objects.get(title='Test event')
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        event = Event.objects.create(
            title='Third test event',
            description='Anything',
            start_time=now - datetime.timedelta(days=20),
            archive_time=now - datetime.timedelta(days=19),
            privacy=Event.PRIVACY_COMPANY,
            status=Event.STATUS_SCHEDULED,
            placeholder_img=event1.placeholder_img,
        )
        assert event in list(Event.objects.archived().all())
        event.channels.add(channel)

        response = self.client.get(reverse('main:channels'))
        eq_(response.status_code, 200)
        ok_('Main' not in response.content)
        ok_('Culture &amp; Context' in response.content)
        ok_('Sub-Culture &amp; Subtle-Context' not in response.content)

        channel_url = reverse('main:home_channels', args=(channel.slug,))
        ok_(channel_url in response.content)
        ok_('1 sub-channel' in response.content)

        # visiting that channel, there should be a link to the sub channel
        response = self.client.get(channel_url)
        eq_(response.status_code, 200)
        ok_('Sub-Culture &amp; Subtle-Context' in response.content)

        event.privacy = Event.PRIVACY_PUBLIC
        event.save()

        response = self.client.get(reverse('main:channels'))
        eq_(response.status_code, 200)
        ok_('1 archived event' in response.content)

        # make it private again
        event.privacy = Event.PRIVACY_COMPANY
        event.save()
        assert Event.objects.archived().all().count() == 1

        # let's say you log in
        User.objects.create_user(
            'worker', 'worker@mozilla.com', 'secret'
        )
        assert self.client.login(username='worker', password='secret')
        response = self.client.get(reverse('main:channels'))
        eq_(response.status_code, 200)
        ok_('1 archived event' in response.content)

        # suppose you log in as a contributor
        contributor = User.objects.create_user(
            'nigel', 'nigel@live.com', 'secret'
        )
        UserProfile.objects.create(
            user=contributor,
            contributor=True
        )
        assert self.client.login(username='nigel', password='secret')
        response = self.client.get(reverse('main:channels'))
        eq_(response.status_code, 200)
        ok_('1 sub-channel' in response.content)

        event.privacy = Event.PRIVACY_CONTRIBUTORS
        event.save()
        response = self.client.get(reverse('main:channels'))
        eq_(response.status_code, 200)
        ok_('1 archived event' in response.content)

    def test_channels_page_without_archived_events(self):
        channel = Channel.objects.create(
            name='Culture & Context',
            slug='culture-and-context',
        )
        url = reverse('main:channels')
        channel_url = reverse('main:home_channels', args=(channel.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(channel_url not in response.content)

        # create an event in that channel
        event1 = Event.objects.get(title='Test event')
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        event = Event.objects.create(
            title='Third test event',
            description='Anything',
            start_time=now + datetime.timedelta(days=1),
            privacy=Event.PRIVACY_PUBLIC,
            status=Event.STATUS_INITIATED,
            placeholder_img=event1.placeholder_img,
        )
        assert event not in list(Event.objects.archived().all())
        assert event not in list(Event.objects.live().all())
        assert event not in list(Event.objects.upcoming().all())
        event.channels.add(channel)

        url = reverse('main:channels')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # still not there because it's not scheduled
        ok_(channel_url not in response.content)

        # make it upcoming
        event.status = Event.STATUS_SCHEDULED
        event.save()
        assert event in list(Event.objects.upcoming().all())

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(channel_url in response.content)

    def test_channel_page(self):
        event1 = Event.objects.get(title='Test event')
        event1.featured = True
        event1.save()

        now = datetime.datetime.utcnow().replace(tzinfo=utc)

        channel = Channel.objects.create(
            name='Culture & Context',
            slug='culture-and-context',
            description="""
            <p>The description</p>
            """,
            image='animage.png',
        )

        event = Event.objects.create(
            title='Second test event',
            slug='second-event',
            description='Anything',
            start_time=now - datetime.timedelta(days=20),
            archive_time=now - datetime.timedelta(days=19),
            privacy=Event.PRIVACY_PUBLIC,
            status=Event.STATUS_SCHEDULED,
            placeholder_img=event1.placeholder_img,
        )
        assert event in list(Event.objects.archived().all())
        event.channels.add(channel)

        event = Event.objects.create(
            title='Third test event',
            description='Anything',
            start_time=now - datetime.timedelta(days=10),
            archive_time=now - datetime.timedelta(days=9),
            privacy=Event.PRIVACY_PUBLIC,
            status=Event.STATUS_SCHEDULED,
            placeholder_img=event1.placeholder_img,
            featured=True,
        )
        assert event in list(Event.objects.archived().all())
        event.channels.add(channel)

        event = Event.objects.create(
            title='Fourth test event',
            description='Anything',
            start_time=now + datetime.timedelta(days=10),
            privacy=Event.PRIVACY_PUBLIC,
            status=Event.STATUS_SCHEDULED,
            placeholder_img=event1.placeholder_img,
        )
        assert event in list(Event.objects.upcoming().all())
        event.channels.add(channel)

        url = reverse('main:home_channels', args=(channel.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('>Culture &amp; Context<' in response.content)
        ok_('<p>The description</p>' in response.content)
        ok_(channel.description in response.content)
        ok_('alt="Culture &amp; Context"' in response.content)

        ok_('Test event' not in response.content)
        ok_('Second test event' in response.content)
        ok_('Third test event' in response.content)

        # because the third event is featured, we'll expect to see it
        # also in the sidebar
        eq_(response.content.count('Third test event'), 2)

        # because it's Upcoming
        ok_('Fourth test event' in response.content)
        # ...but because it's in the alt text too, multiple by 2
        eq_(response.content.count('Fourth test event'), 1 * 2)

        # view the channel page when the image is a banner
        channel.image_is_banner = True
        channel.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('<p>The description</p>' in response.content)

        # view one of them from the channel
        url = reverse('main:event', args=('second-event',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # featured but not this channel
        ok_('Test event' not in response.content)
        # featured but no event hits
        ok_('Third test event' not in response.content)
        # upcoming
        ok_('Fourth test event' in response.content)

    def test_view_channel_in_reverse_order(self):
        channel = Channel.objects.create(
            name='Culture & Context',
            slug='culture-and-context',
            description="""
            <p>The description</p>
            """,
            image='animage.png',
        )
        event = Event.objects.get(title='Test event')
        one = Event.objects.create(
            title='First Title',
            description=event.description,
            start_time=event.start_time - datetime.timedelta(2),
            archive_time=event.start_time - datetime.timedelta(2),
            location=event.location,
            placeholder_img=event.placeholder_img,
            slug='one',
            status=Event.STATUS_SCHEDULED,
            privacy=Event.PRIVACY_PUBLIC,
        )
        one.channels.add(channel)
        two = Event.objects.create(
            title='Second Title',
            description=event.description,
            start_time=event.start_time - datetime.timedelta(1),
            archive_time=event.start_time - datetime.timedelta(1),
            location=event.location,
            placeholder_img=event.placeholder_img,
            slug='two',
            status=Event.STATUS_SCHEDULED,
            privacy=Event.PRIVACY_PUBLIC,
        )
        two.channels.add(channel)

        assert one in Event.objects.archived()
        assert two in Event.objects.archived()

        url = reverse('main:home_channels', args=(channel.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(one.title in response.content)
        ok_(two.title in response.content)
        ok_(
            response.content.find(two.title)
            <
            response.content.find(one.title)
        )

        channel.reverse_order = True
        channel.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(one.title in response.content)
        ok_(two.title in response.content)
        ok_(
            response.content.find(one.title)
            <
            response.content.find(two.title)
        )

    def test_render_home_without_channel(self):
        # if there is no "main" channel it gets automatically created
        self.main_channel.delete()
        ok_(not Channel.objects.filter(slug=settings.DEFAULT_CHANNEL_SLUG))
        response = self.client.get(reverse('main:home'))
        eq_(response.status_code, 200)
        ok_(Channel.objects.filter(slug=settings.DEFAULT_CHANNEL_SLUG))

    def test_render_invalid_channel(self):
        url = reverse('main:home_channels', args=('junk',))
        response = self.client.get(url)
        eq_(response.status_code, 404)

    def test_channel_page_with_pagination(self):
        event1 = Event.objects.get(title='Test event')
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        channel = Channel.objects.create(
            name='Culture & Context',
            slug='culture-and-context',
            description="""
            <p>The description</p>
            """,
            image='animage.png',
        )

        for i in range(1, 40):
            event = Event.objects.create(
                title='%d test event' % i,
                description='Anything',
                start_time=now - datetime.timedelta(days=100 - i),
                archive_time=now - datetime.timedelta(days=99 - i),
                privacy=Event.PRIVACY_PUBLIC,
                status=Event.STATUS_SCHEDULED,
                placeholder_img=event1.placeholder_img,
            )
            event.channels.add(channel)

        url = reverse('main:home_channels', args=(channel.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        prev_url = reverse('main:home_channels', args=(channel.slug, 2))
        next_url = reverse('main:home_channels', args=(channel.slug, 1))
        ok_(prev_url in response.content)
        ok_(next_url not in response.content)

        # go to page 2
        response = self.client.get(prev_url)
        eq_(response.status_code, 200)
        prev_url = reverse('main:home_channels', args=(channel.slug, 3))
        next_url = reverse('main:home_channels', args=(channel.slug, 1))

        ok_(prev_url in response.content)
        ok_(next_url in response.content)

    def test_home_page_with_pagination(self):
        event1 = Event.objects.get(title='Test event')
        now = datetime.datetime.utcnow().replace(tzinfo=utc)

        for i in range(1, 40):
            event = Event.objects.create(
                title='%d test event' % i,
                description='Anything',
                start_time=now - datetime.timedelta(days=100 - i),
                archive_time=now - datetime.timedelta(days=99 - i),
                privacy=Event.PRIVACY_PUBLIC,
                status=Event.STATUS_SCHEDULED,
                placeholder_img=event1.placeholder_img,
            )
            event.channels.add(self.main_channel)

        url = reverse('main:home')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        prev_url = reverse('main:home', args=(2,))
        next_url = reverse('main:home', args=(1,))
        ok_(prev_url in response.content)
        ok_(next_url not in response.content)

        # go to page 2
        response = self.client.get(prev_url)
        eq_(response.status_code, 200)
        prev_url = reverse('main:home', args=(3,))
        next_url = reverse('main:home', args=(1,))

        ok_(prev_url in response.content)
        ok_(next_url in response.content)

    def test_sidebar_static_content(self):
        # create some flat pages
        FlatPage.objects.create(
            url='sidebar_top_main',
            content='<p>Sidebar Top Main</p>'
        )
        FlatPage.objects.create(
            url='sidebar_bottom_main',
            content='<p>Sidebar Bottom Main</p>'
        )
        FlatPage.objects.create(
            url='sidebar_top_testing',
            content='<p>Sidebar Top Testing</p>'
        )
        FlatPage.objects.create(
            url='sidebar_bottom_testing',
            content='<p>Sidebar Bottom Testing</p>'
        )

        response = self.client.get('/')
        ok_('<p>Sidebar Top Main</p>' in response.content)
        ok_('<p>Sidebar Bottom Main</p>' in response.content)
        ok_('<p>Sidebar Top Testing</p>' not in response.content)
        ok_('<p>Sidebar Bottom Testing</p>' not in response.content)

        url = reverse('main:home_channels', args=('testing',))
        response = self.client.get(url)
        ok_('<p>Sidebar Top Main</p>' not in response.content)
        ok_('<p>Sidebar Bottom Main</p>' not in response.content)
        ok_('<p>Sidebar Top Testing</p>' in response.content)
        ok_('<p>Sidebar Bottom Testing</p>' in response.content)

    def test_sidebar_static_content_all_channels(self):
        # create some flat pages
        FlatPage.objects.create(
            url='sidebar_top_*',
            content='<p>Sidebar Top All</p>'
        )
        response = self.client.get('/')
        ok_('<p>Sidebar Top All</p>' in response.content)

        url = reverse('main:home_channels', args=('testing',))
        response = self.client.get(url)
        ok_('<p>Sidebar Top All</p>' in response.content)

    def test_sidebar_static_content_almost_all_channels(self):
        # create some flat pages
        FlatPage.objects.create(
            url='sidebar_top_*',
            content='<p>Sidebar Top All</p>'
        )
        FlatPage.objects.create(
            url='sidebar_top_testing',
            content='<p>Sidebar Top Testing</p>'
        )
        response = self.client.get('/')
        ok_('<p>Sidebar Top All</p>' in response.content)
        ok_('<p>Sidebar Top Testing</p>' not in response.content)

        url = reverse('main:home_channels', args=('testing',))
        response = self.client.get(url)
        ok_('<p>Sidebar Top All</p>' not in response.content)
        ok_('<p>Sidebar Top Testing</p>' in response.content)

    def test_view_event_belonging_to_multiple_channels(self):
        event = Event.objects.get(title='Test event')
        fosdem = Channel.objects.create(
            name='Fosdem',
            slug='fosdem'
        )
        event.channels.add(fosdem)

        url = reverse('main:event', args=(event.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

    def test_event_flatpage_fallback(self):
        flatpage = FlatPage.objects.create(
            url='/test-page',
            title='Flat Test page',
            content='<p>Hi</p>'
        )
        this_site = Site.objects.get(id=settings.SITE_ID)
        flatpage.sites.add(this_site)

        # you can always reach the flatpage by the long URL
        response = self.client.get('/pages/test-page')
        eq_(response.status_code, 200)

        # or from the root
        response = self.client.get('/test-page')
        eq_(response.status_code, 301)
        self.assertRedirects(
            response,
            reverse('main:event', args=('test-page',)),
            status_code=301

        )
        response = self.client.get('/test-page/')
        eq_(response.status_code, 200)
        ok_('Flat Test page' in response.content)

        event = Event.objects.get(slug='test-event')
        response = self.client.get('/test-event/')
        eq_(response.status_code, 200)

        # but if the event takes on a slug that clashes with the
        # flatpage, the flatpage will have to step aside
        event.slug = 'test-page'
        event.save()
        response = self.client.get('/test-page/')
        eq_(response.status_code, 200)
        ok_('Flat Test page' not in response.content)
        ok_(event.title in response.content)

        # but you can still use
        response = self.client.get('/pages/test-page')
        eq_(response.status_code, 200)
        ok_('Flat Test page' in response.content)

        event.slug = 'other-page'
        event.save()
        assert EventOldSlug.objects.get(slug='test-page')
        response = self.client.get('/test-page/')
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=('other-page',))
        )

    def test_link_to_feed_url(self):
        """every page has a link to the feed that depends on how you're
        logged in"""
        self.client.logout()
        url = reverse('main:home')
        feed_url_anonymous = reverse('main:feed', args=('public',))
        feed_url_employee = reverse('main:feed', args=('company',))
        feed_url_contributor = reverse('main:feed', args=('contributors',))

        def extrac_content(content):
            return (
                content
                .split('type="application/rss+xml"')[0]
                .split('<link')[-1]
            )

        response = self.client.get(url)
        eq_(response.status_code, 200)
        content = extrac_content(response.content)
        ok_(feed_url_anonymous in content)
        ok_(feed_url_employee not in content)
        ok_(feed_url_contributor not in content)
        self.client.logout()

        UserProfile.objects.create(
            user=User.objects.create_user(
                'nigel', 'nigel@live.com', 'secret'
            ),
            contributor=True
        )
        contributor = User.objects.get(username='nigel')
        assert contributor.get_profile().contributor
        assert self.client.login(username='nigel', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        content = extrac_content(response.content)
        ok_(feed_url_anonymous not in content)
        ok_(feed_url_employee not in content)
        ok_(feed_url_contributor in content)

        User.objects.create_user(
            'zandr', 'zandr@mozilla.com', 'secret'
        )
        assert self.client.login(username='zandr', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        content = extrac_content(response.content)
        ok_(feed_url_anonymous not in content)
        ok_(feed_url_employee in content)
        ok_(feed_url_contributor not in content)

    def test_view_event_video_only(self):
        event = Event.objects.get(title='Test event')
        assert event.privacy == Event.PRIVACY_PUBLIC  # default
        url = reverse('main:event_video', kwargs={'slug': event.slug})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response['X-Frame-Options'], 'ALLOWALL')
        ok_(event.title in response.content)

    def test_view_event_video_only_not_public(self):
        event = Event.objects.get(title='Test event')
        event.privacy = Event.PRIVACY_COMPANY
        event.save()

        url = reverse('main:event_video', kwargs={'slug': event.slug})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response['X-Frame-Options'], 'ALLOWALL')
        ok_("Not a public event" in response.content)

        # it won't help to be signed in
        User.objects.create_user(
            'zandr', 'zandr@mozilla.com', 'secret'
        )
        assert self.client.login(username='zandr', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response['X-Frame-Options'], 'ALLOWALL')
        ok_("Not a public event" in response.content)

        # but that's ignored if you set the ?embedded=false
        response = self.client.get(url, {'embedded': False})
        eq_(response.status_code, 200)
        ok_("Not a public event" not in response.content)
        eq_(response['X-Frame-Options'], 'DENY')  # back to the default

    def test_view_event_video_not_found(self):
        url = reverse('main:event_video', kwargs={'slug': 'xxxxxx'})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response['X-Frame-Options'], 'ALLOWALL')
        ok_("Event not found" in response.content)

    def test_tag_cloud(self):
        url = reverse('main:tag_cloud')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # add some events
        events = []
        event1 = Event.objects.get(title='Test event')
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        for i in range(1, 10):
            event = Event.objects.create(
                title='%d test event' % i,
                description='Anything',
                start_time=now - datetime.timedelta(days=100 - i),
                archive_time=now - datetime.timedelta(days=99 - i),
                privacy=Event.PRIVACY_PUBLIC,
                status=Event.STATUS_SCHEDULED,
                placeholder_img=event1.placeholder_img,
            )
            event.channels.add(self.main_channel)
            events.append(event)

        tag1 = Tag.objects.create(name='Tag1')
        tag2 = Tag.objects.create(name='Tag2')
        tag3 = Tag.objects.create(name='Tag3')
        tag4 = Tag.objects.create(name='Tag4')
        tag5 = Tag.objects.create(name='Tag5')
        events[0].tags.add(tag1)
        events[0].tags.add(tag2)
        events[0].save()
        events[1].tags.add(tag1)
        events[1].save()
        events[2].tags.add(tag2)
        events[2].save()
        events[3].tags.add(tag3)
        events[3].save()

        events[4].tags.add(tag3)
        events[4].tags.add(tag4)
        events[4].privacy = Event.PRIVACY_CONTRIBUTORS
        events[4].save()

        events[5].tags.add(tag5)
        events[5].privacy = Event.PRIVACY_COMPANY
        events[5].save()

        events[6].tags.add(tag5)
        events[6].privacy = Event.PRIVACY_COMPANY
        events[6].save()

        response = self.client.get(url)
        eq_(response.status_code, 200)

        ok_(tag1.name in response.content)
        ok_(tag2.name in response.content)
        ok_(tag3.name not in response.content)

        # view it as a contributor
        UserProfile.objects.create(
            user=User.objects.create_user(
                'nigel', 'nigel@live.com', 'secret'
            ),
            contributor=True
        )
        assert self.client.login(username='nigel', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(tag1.name in response.content)
        ok_(tag2.name in response.content)
        ok_(tag3.name in response.content)
        ok_(tag5.name not in response.content)

        # view it as a regular signed in person
        User.objects.create_user(
            'zandr', 'zandr@mozilla.com', 'secret'
        )
        assert self.client.login(username='zandr', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        ok_(tag1.name in response.content)
        ok_(tag2.name in response.content)
        ok_(tag3.name in response.content)
        ok_(tag5.name in response.content)

    def test_all_tags(self):
        url = reverse('main:all_tags')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(
            sorted(data['tags']),
            sorted(x.name for x in Tag.objects.all())
        )

    def test_calendar_page(self):
        url = reverse('main:calendar')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data_url = reverse('main:calendar_data')
        ok_(data_url in response.content)
        calendars_url = reverse('main:calendars')
        ok_(calendars_url in response.content)

    def test_calendar_data(self):
        url = reverse('main:calendar_data')
        response = self.client.get(url)
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'start': '123',
            'end': 'not a number'
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'start': 'not a number',
            'end': '123'
        })
        eq_(response.status_code, 400)

        first = datetime.datetime.now()
        while first.day != 1:
            first -= datetime.timedelta(days=1)
        first = first.date()
        last = first
        while last.month == first.month:
            last += datetime.timedelta(days=1)

        first_ts = int(time.mktime(first.timetuple()))
        last_ts = int(time.mktime(last.timetuple()))

        # start > end
        response = self.client.get(url, {
            'start': last_ts,
            'end': first_ts
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'start': first_ts,
            'end': last_ts
        })
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        test_event = Event.objects.get(title='Test event')
        assert test_event.start_time.date() >= first
        assert test_event.start_time.date() < last

        assert len(structure) == 1
        item, = structure
        eq_(item['title'], test_event.title)
        eq_(item['url'], reverse('main:event', args=(test_event.slug,)))

    def test_calendar_data_privacy(self):
        url = reverse('main:calendar_data')
        response = self.client.get(url)

        first = datetime.datetime.now()
        while first.day != 1:
            first -= datetime.timedelta(days=1)
        first = first.date()
        last = first
        while last.month == first.month:
            last += datetime.timedelta(days=1)

        first_ts = int(time.mktime(first.timetuple()))
        last_ts = int(time.mktime(last.timetuple()))

        params = {
            'start': first_ts,
            'end': last_ts
        }
        response = self.client.get(url, params)
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        event = Event.objects.get(title='Test event')
        assert first <= event.start_time.date() <= last
        item, = structure
        eq_(item['title'], event.title)

        # make it only available to contributors (and staff of course)
        event.privacy = Event.PRIVACY_CONTRIBUTORS
        event.save()
        response = self.client.get(url, params)
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        ok_(not structure)

        contributor = User.objects.create_user(
            'nigel', 'nigel@live.com', 'secret'
        )
        UserProfile.objects.create(
            user=contributor,
            contributor=True
        )
        assert self.client.login(username='nigel', password='secret')
        response = self.client.get(url, params)
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        ok_(structure)

        event.privacy = Event.PRIVACY_COMPANY
        event.save()
        response = self.client.get(url, params)
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        ok_(not structure)

        User.objects.create_user(
            'worker', 'worker@mozilla.com', 'secret'
        )
        assert self.client.login(username='worker', password='secret')
        response = self.client.get(url, params)
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        ok_(structure)

    def test_calendar_data_bogus_dates(self):
        url = reverse('main:calendar_data')

        response = self.client.get(url, {
            'start': '1393196400',
            'end': '4444444444444444'
        })
        eq_(response.status_code, 400)

    def test_open_graph_details(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        assert os.path.isfile(event.placeholder_img.path)

        url = reverse('main:event', args=(event.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        head = response.content.split('</head>')[0]
        ok_('<meta property="og:title" content="%s">' % event.title in head)
        from airmozilla.main.helpers import short_desc
        ok_(
            '<meta property="og:description" content="%s">' % short_desc(event)
            in head
        )
        ok_('<meta property="og:image" content="htt' in head)
        absolute_url = 'http://testserver' + url
        ok_('<meta property="og:url" content="%s">' % absolute_url in head)

    def test_meta_keywords(self):
        event = Event.objects.get(title='Test event')
        event.save()

        event.tags.add(Tag.objects.create(name="One"))
        event.tags.add(Tag.objects.create(name="Two"))

        url = reverse('main:event', args=(event.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        head = response.content.split('</head>')[0]

        content = re.findall(
            '<meta name="keywords" content="([^\"]+)">',
            head
        )[0]
        ok_("One" in content)
        ok_("Two" in content)

    def test_featured_in_sidebar(self):
        # use the calendar page so that we only get events that appear
        # in the side bar
        url = reverse('main:calendar')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Trending' not in response.content)

        # set up 3 events
        event0 = Event.objects.get(title='Test event')
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        event1 = Event.objects.create(
            title='1 Test Event',
            description='Anything',
            start_time=now - datetime.timedelta(days=3),
            archive_time=now - datetime.timedelta(days=2),
            privacy=Event.PRIVACY_PUBLIC,
            status=Event.STATUS_SCHEDULED,
            placeholder_img=event0.placeholder_img,
        )
        event1.channels.add(self.main_channel)
        event2 = Event.objects.create(
            title='2 Test Event',
            description='Anything',
            start_time=now - datetime.timedelta(days=4),
            archive_time=now - datetime.timedelta(days=3),
            privacy=Event.PRIVACY_PUBLIC,
            status=Event.STATUS_SCHEDULED,
            placeholder_img=event0.placeholder_img,
        )
        event2.channels.add(self.main_channel)
        event3 = Event.objects.create(
            title='3 Test Event',
            description='Anything',
            start_time=now - datetime.timedelta(days=5),
            archive_time=now - datetime.timedelta(days=4),
            privacy=Event.PRIVACY_PUBLIC,
            status=Event.STATUS_SCHEDULED,
            placeholder_img=event0.placeholder_img,
        )
        event3.channels.add(self.main_channel)

        # now, we can expect all of these three to appear in the side bar
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # because they don't have any EventHitStats for these
        ok_('Trending' not in response.content)
        EventHitStats.objects.create(
            event=event1,
            total_hits=1000,
            shortcode='abc123'
        )
        EventHitStats.objects.create(
            event=event2,
            total_hits=1000,
            shortcode='xyz123'
        )
        stats3 = EventHitStats.objects.create(
            event=event3,
            total_hits=1000,
            shortcode='xyz987'
        )

        # to reset the cache on the sidebar queries, some event
        # needs to change
        event3.save()

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Trending' in response.content)
        ok_(event1.title in response.content)
        ok_(event2.title in response.content)
        ok_(event3.title in response.content)
        # event 1 is top-most because it's the youngest
        ok_(
            response.content.find(event1.title) <
            response.content.find(event2.title) <
            response.content.find(event3.title)
        )

        # boost event3 by making it featured
        event3.featured = True
        event3.save()
        # event3 is 3 days old, has 1000 views, thus
        # score = 2*1000 / 3 ^ 1.8 ~= 276
        # but event2 is 2 days old and same number of view, thus
        # score = 1000 / 2 ^ 1.8 ~= 287
        # so, give event3 a couple more events
        stats3.total_hits += 100
        stats3.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # event 1 is top-most because it's the youngest
        # but now event3 has gone up a bit
        ok_(
            response.content.find(event1.title) <
            response.content.find(event3.title) <
            response.content.find(event2.title)
        )

        # now, let's make event2 be part of a channel that is supposed to be
        # excluded from the Trending sidebar
        poison = Channel.objects.create(
            name='Poisonous',
            exclude_from_trending=True
        )
        event2.channels.add(poison)
        all_but_event2 = Event.objects.exclude(
            channels__exclude_from_trending=True
        )
        assert event2 not in all_but_event2
        cache.clear()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # print response.content
        # event 1 is top-most because it's the youngest
        # but now event3 has gone up a bit
        ok_(event2.title not in response.content)

    def test_featured_sidebar_for_contributors(self):
        """if you're a contributor your shouldn't be tempted to see private
        events in the sidebar of featured events"""

        # use the calendar page so that we only get events that appear
        # in the side bar
        url = reverse('main:calendar')
        # set up 3 events
        event0 = Event.objects.get(title='Test event')
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        event1 = Event.objects.create(
            title='1 Test Event',
            description='Anything',
            start_time=now - datetime.timedelta(days=3),
            archive_time=now - datetime.timedelta(days=2),
            privacy=Event.PRIVACY_PUBLIC,
            status=Event.STATUS_SCHEDULED,
            placeholder_img=event0.placeholder_img,
        )
        event1.channels.add(self.main_channel)
        event2 = Event.objects.create(
            title='2 Test Event',
            description='Anything',
            start_time=now - datetime.timedelta(days=4),
            archive_time=now - datetime.timedelta(days=3),
            privacy=Event.PRIVACY_CONTRIBUTORS,
            status=Event.STATUS_SCHEDULED,
            placeholder_img=event0.placeholder_img,
        )
        event2.channels.add(self.main_channel)
        event3 = Event.objects.create(
            title='3 Test Event',
            description='Anything',
            start_time=now - datetime.timedelta(days=5),
            archive_time=now - datetime.timedelta(days=4),
            privacy=Event.PRIVACY_COMPANY,
            status=Event.STATUS_SCHEDULED,
            placeholder_img=event0.placeholder_img,
        )
        event3.channels.add(self.main_channel)
        EventHitStats.objects.create(
            event=event1,
            total_hits=1000,
            shortcode='abc123'
        )
        EventHitStats.objects.create(
            event=event2,
            total_hits=1000,
            shortcode='xyz123'
        )
        EventHitStats.objects.create(
            event=event3,
            total_hits=1000,
            shortcode='xyz987'
        )

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Trending' in response.content)
        ok_(event1.title in response.content)
        ok_(event2.title not in response.content)
        ok_(event3.title not in response.content)

        # sign in as a contributor
        UserProfile.objects.create(
            user=User.objects.create_user(
                'peterbe', 'peterbe@gmail.com', 'secret'
            ),
            contributor=True
        )
        assert self.client.login(username='peterbe', password='secret')

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Trending' in response.content)
        ok_(event1.title in response.content)
        ok_(event2.title in response.content)
        ok_(event3.title not in response.content)

        # sign in as staff
        User.objects.create_user(
            'zandr', 'zandr@mozilla.com', 'secret'
        )
        assert self.client.login(username='zandr', password='secret')

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Trending' in response.content)
        ok_(event1.title in response.content)
        ok_(event2.title in response.content)
        ok_(event3.title in response.content)

    @mock.patch('logging.error')
    @mock.patch('requests.get')
    def test_view_curated_group_event(self, rget, rlogging):

        def mocked_get(url, **options):
            if 'peterbe' in url:
                return Response(VOUCHED_FOR)
            if 'offset=0' in url:
                return Response(GROUPS1)
            if 'offset=500' in url:
                return Response(GROUPS2)
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        # sign in as a contributor
        UserProfile.objects.create(
            user=User.objects.create_user(
                'peterbe', 'peterbe@gmail.com', 'secret'
            ),
            contributor=True
        )
        assert self.client.login(username='peterbe', password='secret')

        event = Event.objects.get(title='Test event')
        event.privacy = Event.PRIVACY_COMPANY
        event.save()

        url = reverse('main:event', args=(event.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 302)
        permission_denied_url = reverse(
            'main:permission_denied',
            args=(event.slug,)
        )
        self.assertRedirects(response, permission_denied_url)

        event.privacy = Event.PRIVACY_CONTRIBUTORS
        event.save()

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.title in response.content)

        # make it so that viewing the event requires that you're a
        # certain group
        vip_group = CuratedGroup.objects.create(
            event=event,
            name='vip',
            url='https://mozillians.org/vip',
        )
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self.assertRedirects(response, permission_denied_url)
        # and view that page
        response = self.client.get(permission_denied_url)
        eq_(response.status_code, 200)
        ok_(vip_group.url in response.content)

        CuratedGroup.objects.create(
            event=event,
            name='ugly tuna',
            url='https://mozillians.org/ugly-tuna',
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(re.findall(
            'This event is available only to staff and Mozilla volunteers '
            'who are members of the\s+ugly tuna\s+or\s+vip\s+group.',
            response.content,
            re.M
        ))

    @mock.patch('logging.error')
    @mock.patch('requests.get')
    def test_view_curated_group_event_as_staff(self, rget, rlogging):

        def mocked_get(url, **options):
            if 'peterbe' in url:
                return Response(VOUCHED_FOR)
            if 'offset=0' in url:
                return Response(GROUPS1)
            if 'offset=500' in url:
                return Response(GROUPS2)
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        # sign in as a member of staff
        User.objects.create_user(
            'mary', 'mary@mozilla.com', 'secret'
        )
        assert self.client.login(username='mary', password='secret')

        event = Event.objects.get(title='Test event')
        event.privacy = Event.PRIVACY_CONTRIBUTORS
        event.save()

        url = reverse('main:event', args=(event.slug,))

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.title in response.content)

        # make it so that viewing the event requires that you're a
        # certain group
        CuratedGroup.objects.create(
            event=event,
            name='vip',
            url='https://mozillians.org/vip',
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.title in response.content)

    def test_view_removed_event(self):
        event = Event.objects.get(title='Test event')
        url = reverse('main:event', args=(event.slug,))

        response = self.client.get(url)
        eq_(response.status_code, 200)

        event.status = Event.STATUS_REMOVED
        event.save()

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('This event is no longer available.' in response.content)
        ok_(event.title in response.content)

        # let's view it as a signed in user
        # shouldn't make a difference
        user = self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('This event is no longer available.' in response.content)
        ok_(event.title in response.content)

        # but if signed in as a superuser, you can view it
        user.is_superuser = True
        user.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('This event is no longer available.' not in response.content)
        ok_(event.title in response.content)
        # but there is a flash message warning on the page that says...
        ok_(
            'Event is not publicly visible - not scheduled.'
            in response.content
        )

    def test_edgecast_smil(self):
        url = reverse('main:edgecast_smil')
        response = self.client.get(url, {
            'venue': 'Something',
            'token': 'XXXX'
        })
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'application/smil')
        eq_(response['Access-Control-Allow-Origin'], '*')
        ok_('XXXX' in response.content)
        ok_('/Restricted/' in response.content)
        ok_('Something' in response.content)

        # do it once without `token`
        response = self.client.get(url, {
            'venue': 'Something',
        })
        eq_(response.status_code, 200)
        ok_('/Restricted/' not in response.content)
        ok_('Something' in response.content)

    def test_crossdomain_xml(self):
        url = reverse('main:crossdomain_xml')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'text/xml')
        eq_(response['Access-Control-Allow-Origin'], '*')
        ok_('<allow-access-from domain="*" />' in response.content)

    def test_picture_over_placeholder(self):
        event = Event.objects.get(title='Test event')
        assert event in Event.objects.live()
        self._attach_file(event, self.main_image)
        assert os.path.isfile(event.placeholder_img.path)

        response = self.client.get('/')
        assert event.title in response.content
        doc = pyquery.PyQuery(response.content)
        img, = doc('.tag-live img')
        eq_(img.attrib['width'], '160')
        live_src = img.attrib['src']

        with open(self.main_image) as fp:
            picture = Picture.objects.create(file=File(fp))
            event.picture = picture
            event.save()

        response = self.client.get('/')
        assert event.title in response.content
        doc = pyquery.PyQuery(response.content)
        img, = doc('.tag-live img')
        live_src_after = img.attrib['src']
        ok_(live_src != live_src_after)

        # make it not a live event
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        yesterday = now - datetime.timedelta(days=1)
        event.archive_time = yesterday
        event.start_time = yesterday
        event.picture = None
        event.save()

        assert event not in Event.objects.live()
        assert event in Event.objects.archived()

        response = self.client.get('/')
        assert event.title in response.content
        doc = pyquery.PyQuery(response.content)
        img, = doc('article img')
        eq_(img.attrib['width'], '68')
        archived_src = img.attrib['src']

        # put the picture back on
        event.picture = picture
        event.save()
        response = self.client.get('/')
        doc = pyquery.PyQuery(response.content)
        img, = doc('article img')
        archived_src_after = img.attrib['src']
        ok_(archived_src_after != archived_src)

        # now make it appear in the upcoming
        event.archive_time = None
        tomorrow = now + datetime.timedelta(days=1)
        event.start_time = tomorrow
        event.picture = None
        event.save()

        assert event not in Event.objects.live()
        assert event not in Event.objects.archived()
        assert event in Event.objects.upcoming()

        response = self.client.get('/')
        assert event.title in response.content
        doc = pyquery.PyQuery(response.content)
        img, = doc('aside img')  # side event
        eq_(img.attrib['width'], '68')
        upcoming_src = img.attrib['src']

        # put the picture back on
        event.picture = picture
        event.save()
        response = self.client.get('/')
        doc = pyquery.PyQuery(response.content)
        img, = doc('aside img')
        upcoming_src_after = img.attrib['src']
        ok_(upcoming_src_after != upcoming_src)


class TestEventEdit(DjangoTestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']
    main_image = 'airmozilla/manage/tests/firefox.png'
    other_image = 'airmozilla/manage/tests/other_logo.png'
    third_image = 'airmozilla/manage/tests/other_logo_reversed.png'

    def _event_to_dict(self, event):
        from airmozilla.main.views import EventEditView
        return EventEditView.event_to_dict(event)

    def test_link_to_edit(self):
        event = Event.objects.get(title='Test event')
        response = self.client.get(reverse('main:event', args=(event.slug,)))
        eq_(response.status_code, 200)

        url = reverse('main:event_edit', args=(event.slug,))
        ok_(url not in response.content)
        self._login()
        response = self.client.get(reverse('main:event', args=(event.slug,)))
        eq_(response.status_code, 200)
        ok_(url in response.content)

    def test_cant_view(self):
        event = Event.objects.get(title='Test event')
        url = reverse('main:event_edit', args=(event.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=(event.slug,))
        )
        response = self.client.post(url, {})
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=(event.slug,))
        )

    def test_edit_title(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        url = reverse('main:event_edit', args=(event.slug,))

        response = self.client.get(url)
        eq_(response.status_code, 302)

        user = self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)

        data = self._event_to_dict(event)
        previous = json.dumps(data)

        data = {
            'previous': previous,
            'title': 'Different title',
            'short_description': event.short_description,
            'description': event.description,
            'additional_links': event.additional_links,
            'tags': ', '.join(x.name for x in event.tags.all()),
            'channels': [x.pk for x in event.channels.all()]
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=(event.slug,))
        )
        # this should have created 2 EventRevision objects.
        initial, current = EventRevision.objects.all().order_by('created')
        eq_(initial.event, event)
        eq_(current.event, event)
        eq_(initial.user, None)
        eq_(current.user, user)

        eq_(initial.title, 'Test event')
        eq_(current.title, 'Different title')
        # reload the event
        event = Event.objects.get(pk=event.pk)
        eq_(event.title, 'Different title')

    def test_edit_nothing(self):
        """basically pressing save without changing anything"""
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        url = reverse('main:event_edit', args=(event.slug,))

        data = self._event_to_dict(event)
        previous = json.dumps(data)

        data = {
            'previous': previous,
            'title': event.title,
            'short_description': event.short_description,
            'description': event.description,
            'additional_links': event.additional_links,
            'tags': ', '.join(x.name for x in event.tags.all()),
            'channels': [x.pk for x in event.channels.all()]
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=(event.slug,))
        )
        self._login()
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        ok_(not EventRevision.objects.all())

    def test_bad_edit_title(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        url = reverse('main:event_edit', args=(event.slug,))
        self._login()

        data = self._event_to_dict(event)
        previous = json.dumps(data)

        data = {
            'previous': previous,
            'title': '',
            'short_description': event.short_description,
            'description': event.description,
            'additional_links': event.additional_links,
            'tags': ', '.join(x.name for x in event.tags.all()),
            'channels': [x.pk for x in event.channels.all()]
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 200)
        ok_('This field is required' in response.content)

    def test_edit_on_bad_url(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        url = reverse('main:event_edit', args=('xxx',))

        response = self.client.get(url)
        eq_(response.status_code, 404)

        old_slug = event.slug
        event.slug = 'new-slug'
        event.save()

        data = self._event_to_dict(event)
        previous = json.dumps(data)
        data = {
            'previous': previous,
            'title': event.title,
            'short_description': event.short_description,
            'description': event.description,
            'additional_links': event.additional_links,
            'tags': ', '.join(x.name for x in event.tags.all()),
            'channels': [x.pk for x in event.channels.all()]
        }

        url = reverse('main:event_edit', args=(old_slug,))
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=(event.slug,))
        )
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=(event.slug,))
        )

        url = reverse('main:event_edit', args=(event.slug,))
        response = self.client.get(url)
        # because you're not allowed to view it
        eq_(response.status_code, 302)

        url = reverse('main:event_edit', args=(event.slug,))
        response = self.client.post(url, data)
        # because you're not allowed to view it, still
        eq_(response.status_code, 302)

    def test_edit_all_simple_fields(self):
        """similar to test_edit_title() but changing all fields
        other than the placeholder_img
        """
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        assert event.tags.all()
        assert event.channels.all()
        url = reverse('main:event_edit', args=(event.slug,))
        self._login()

        data = self._event_to_dict(event)
        previous = json.dumps(data)

        new_channel = Channel.objects.create(
            name='New Stuff',
            slug='new-stuff'
        )
        new_channel2 = Channel.objects.create(
            name='New Stuff II',
            slug='new-stuff-2'
        )
        data = {
            'previous': previous,
            'title': 'Different title',
            'short_description': 'new short description',
            'description': 'new description',
            'additional_links': 'new additional_links',
            'tags': 'newtag',
            'channels': [new_channel.pk, new_channel2.pk]
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=(event.slug,))
        )
        # this should have created 2 EventRevision objects.
        initial, current = EventRevision.objects.all().order_by('created')
        eq_(initial.event, event)
        eq_(initial.title, 'Test event')
        eq_(current.title, 'Different title')
        # reload the event
        event = Event.objects.get(pk=event.pk)
        eq_(event.title, 'Different title')
        eq_(event.description, 'new description')
        eq_(event.short_description, 'new short description')
        eq_(event.additional_links, 'new additional_links')
        eq_(
            sorted(x.name for x in event.tags.all()),
            ['newtag']
        )
        eq_(
            sorted(x.name for x in event.channels.all()),
            ['New Stuff', 'New Stuff II']
        )

    def test_edit_recruitmentmessage(self):
        """Change the revision message from nothing, to something
        to another one.
        """
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        assert event.tags.all()
        assert event.channels.all()
        url = reverse('main:event_edit', args=(event.slug,))
        user = self._login()

        data = self._event_to_dict(event)
        previous = json.dumps(data)

        msg1 = RecruitmentMessage.objects.create(
            text='Web Developer',
            url='http://careers.mozilla.com/123',
            active=True
        )
        msg2 = RecruitmentMessage.objects.create(
            text='C++ Developer',
            url='http://careers.mozilla.com/456',
            active=True
        )
        msg3 = RecruitmentMessage.objects.create(
            text='Fortran Developer',
            url='http://careers.mozilla.com/000',
            active=False  # Note!
        )

        # if you don't have the right permission, you can't see this choice
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Recruitment message' not in response.content)

        # give the user the necessary permission
        recruiters = Group.objects.create(name='Recruiters')
        permission = Permission.objects.get(
            codename='change_recruitmentmessage'
        )
        recruiters.permissions.add(permission)
        user.groups.add(recruiters)
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Recruitment message' in response.content)
        ok_(msg1.text in response.content)
        ok_(msg2.text in response.content)
        ok_(msg3.text not in response.content)  # not active

        data = {
            'previous': previous,
            'recruitmentmessage': msg1.pk,
            'title': event.title,
            'description': event.description,
            'short_description': event.short_description,
            'channels': [x.id for x in event.channels.all()],
            'tags': [x.name for x in event.tags.all()],
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=(event.slug,))
        )

        # this should have created 2 EventRevision objects.
        initial, current = EventRevision.objects.all().order_by('created')
        eq_(initial.event, event)
        ok_(not initial.recruitmentmessage)
        eq_(current.recruitmentmessage, msg1)

        # reload the event
        event = Event.objects.get(pk=event.pk)
        eq_(event.recruitmentmessage, msg1)

        # now change it to another message
        data = self._event_to_dict(event)
        previous = json.dumps(data)
        data['recruitmentmessage'] = msg2.pk
        data['previous'] = previous
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=(event.slug,))
        )
        # reload the event
        event = Event.objects.get(pk=event.pk)
        eq_(event.recruitmentmessage, msg2)

        initial, __, current = (
            EventRevision.objects.all().order_by('created')
        )
        eq_(current.recruitmentmessage, msg2)

        # lastly, change it to blank
        data = self._event_to_dict(event)
        previous = json.dumps(data)
        data['recruitmentmessage'] = ''
        data['previous'] = previous
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=(event.slug,))
        )
        # reload the event
        event = Event.objects.get(pk=event.pk)
        eq_(event.recruitmentmessage, None)

        initial, __, __, current = (
            EventRevision.objects.all().order_by('created')
        )
        eq_(current.recruitmentmessage, None)

    def test_edit_placeholder_img(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        url = reverse('main:event_edit', args=(event.slug,))
        self._login()

        old_placeholder_img_path = event.placeholder_img.path

        data = self._event_to_dict(event)
        previous = json.dumps(data)

        with open(self.other_image) as fp:
            data = {
                'previous': previous,
                'title': event.title,
                'short_description': event.short_description,
                'description': event.description,
                'additional_links': event.additional_links,
                'tags': ', '.join(x.name for x in event.tags.all()),
                'channels': [x.pk for x in event.channels.all()],
                'placeholder_img': fp,
            }
            response = self.client.post(url, data)
            eq_(response.status_code, 302)
            self.assertRedirects(
                response,
                reverse('main:event', args=(event.slug,))
            )
        # this should have created 2 EventRevision objects.
        initial, current = EventRevision.objects.all().order_by('created')
        ok_(initial.placeholder_img)
        ok_(current.placeholder_img)
        # reload the event
        event = Event.objects.get(pk=event.pk)
        new_placeholder_img_path = event.placeholder_img.path
        ok_(old_placeholder_img_path != new_placeholder_img_path)
        ok_(os.path.isfile(old_placeholder_img_path))
        ok_(os.path.isfile(new_placeholder_img_path))

    def test_edit_conflict(self):
        """You can't edit the title if someone else edited it since the
        'previous' JSON dump was taken."""
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        url = reverse('main:event_edit', args=(event.slug,))
        self._login()

        data = self._event_to_dict(event)
        previous = json.dumps(data)

        event.title = 'Sneak Edit'
        event.save()

        data = {
            'previous': previous,
            'title': 'Different title',
            'short_description': event.short_description,
            'description': event.description,
            'additional_links': event.additional_links,
            'tags': ', '.join(x.name for x in event.tags.all()),
            'channels': [x.pk for x in event.channels.all()]
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 200)
        ok_('Conflict error!' in response.content)

    def test_edit_conflict_on_placeholder_img(self):
        """You can't edit the title if someone else edited it since the
        'previous' JSON dump was taken."""
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        url = reverse('main:event_edit', args=(event.slug,))
        self._login()

        data = self._event_to_dict(event)
        previous = json.dumps(data)

        self._attach_file(event, self.other_image)

        with open(self.third_image) as fp:
            data = {
                'previous': previous,
                'title': event.title,
                'short_description': event.short_description,
                'description': event.description,
                'additional_links': event.additional_links,
                'tags': ', '.join(x.name for x in event.tags.all()),
                'channels': [x.pk for x in event.channels.all()],
                'placeholder_img': fp
            }
            response = self.client.post(url, data)
            eq_(response.status_code, 200)
            ok_('Conflict error!' in response.content)

    def test_edit_conflict_near_miss(self):
        """If the event changes between the time you load the edit page
        and you pressing 'Save' it shouldn't be a problem as long as
        you're changing something different."""
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        url = reverse('main:event_edit', args=(event.slug,))
        self._login()

        data = self._event_to_dict(event)
        previous = json.dumps(data)

        event.title = 'Sneak Edit'
        event.save()

        data = {
            'previous': previous,
            'title': 'Test event',
            'short_description': 'new short description',
            'description': event.description,
            'additional_links': event.additional_links,
            'tags': ', '.join(x.name for x in event.tags.all()),
            'channels': [x.pk for x in event.channels.all()]
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        event = Event.objects.get(pk=event.pk)
        eq_(event.title, 'Sneak Edit')
        eq_(event.short_description, 'new short description')

    def test_view_revision_change_links(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        url = reverse('main:event_edit', args=(event.slug,))
        user = self._login()

        data = self._event_to_dict(event)
        previous = json.dumps(data)

        data = {
            'previous': previous,
            'title': 'Test event',
            'short_description': 'new short description',
            'description': event.description,
            'additional_links': event.additional_links,
            'tags': ', '.join(x.name for x in event.tags.all()),
            'channels': [x.pk for x in event.channels.all()]
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)

        eq_(EventRevision.objects.filter(event=event).count(), 2)
        base_revision = EventRevision.objects.get(
            event=event,
            user__isnull=True
        )
        user_revision = EventRevision.objects.get(
            event=event,
            user=user
        )

        # reload the event edit page
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # because there's no difference between this and the event now
        # we should NOT have a link to see the difference for the user_revision
        ok_(
            reverse('main:event_difference',
                    args=(event.slug, user_revision.pk))
            not in response.content
        )
        # but there should be a link to the change
        ok_(
            reverse('main:event_change',
                    args=(event.slug, user_revision.pk))
            in response.content
        )
        # since the base revision doesn't have any changes there shouldn't
        # be a link to it
        ok_(
            reverse('main:event_change',
                    args=(event.slug, base_revision.pk))
            not in response.content
        )
        # but there should be a link to the change
        ok_(
            reverse('main:event_difference',
                    args=(event.slug, base_revision.pk))
            in response.content
        )

    def test_cant_view_all_revision_changes(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)

        # base revision
        base_revision = EventRevision.objects.create_from_event(event)

        # change the event without saving so we can make a new revision
        event.title = 'Different title'
        user = User.objects.create_user(
            'mary', 'mary@mozilla.com', 'secret'
        )
        user_revision = EventRevision.objects.create_from_event(
            event,
            user=user
        )
        change_url = reverse(
            'main:event_change',
            args=(event.slug, user_revision.pk)
        )
        difference_url = reverse(
            'main:event_difference',
            args=(event.slug, base_revision.pk)
        )
        # you're not allowed to view these if you're not signed in
        response = self.client.get(change_url)
        eq_(response.status_code, 302)

        response = self.client.get(difference_url)
        eq_(response.status_code, 302)

    def test_view_revision_change(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)

        # base revision
        base_revision = EventRevision.objects.create_from_event(event)

        # change the event without saving so we can make a new revision
        event.title = 'Different title'
        event.description = 'New description'
        event.short_description = 'New short description'
        event.additional_links = 'New additional links'
        event.save()
        user = User.objects.create_user(
            'bob', 'bob@mozilla.com', 'secret'
        )
        user_revision = EventRevision.objects.create_from_event(
            event,
            user=user
        )
        user_revision.tags.add(Tag.objects.create(name='newtag'))
        user_revision.channels.remove(Channel.objects.get(name='Main'))
        user_revision.channels.add(
            Channel.objects.create(name='Web dev', slug='webdev')
        )
        with open(self.other_image, 'rb') as f:
            img = File(f)
            user_revision.placeholder_img.save(
                os.path.basename(self.other_image),
                img
            )

        # view the change
        url = reverse('main:event_change', args=(event.slug, user_revision.pk))
        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Different title' in response.content)
        ok_('New description' in response.content)
        ok_('New short description' in response.content)
        ok_('New additional links' in response.content)
        ok_('Web dev' in response.content)
        ok_('newtag, testing' in response.content)

        event.tags.add(Tag.objects.create(name='newtag'))
        event.channels.remove(Channel.objects.get(name='Main'))
        event.channels.add(
            Channel.objects.get(name='Web dev')
        )

        # view the difference
        url = reverse(
            'main:event_difference',
            args=(event.slug, base_revision.pk))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Different title' in response.content)
        ok_('New description' in response.content)
        ok_('New short description' in response.content)
        ok_('New additional links' in response.content)
        ok_('Web dev' in response.content)
        ok_('newtag, testing' in response.content)

    def test_view_revision_change_on_recruitmentmessage(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)

        # base revision
        EventRevision.objects.create_from_event(event)

        user = User.objects.create_user(
            'bob', 'bob@mozilla.com', 'secret'
        )
        user_revision = EventRevision.objects.create_from_event(
            event,
            user=user
        )
        msg1 = RecruitmentMessage.objects.create(
            text='Web Developer',
            url='http://careers.mozilla.com/123',
            active=True
        )
        user_revision.recruitmentmessage = msg1
        user_revision.save()

        # view the change
        url = reverse('main:event_change', args=(event.slug, user_revision.pk))
        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(msg1.text in response.content)
