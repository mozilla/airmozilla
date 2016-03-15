import datetime
import httplib
import json
import urllib2
import urllib
import copy
import os
import re

from nose.tools import eq_, ok_
import mock
import pyquery

from django.contrib.auth.models import Group, User, AnonymousUser
from django.utils import timezone
from django.utils.timezone import utc
from django.conf import settings
from django.core.cache import cache
from django.core.files import File
from django.core.urlresolvers import reverse
from django.utils.encoding import smart_text

from airmozilla.main.models import (
    Approval,
    Event,
    EventOldSlug,
    Tag,
    UserProfile,
    Channel,
    Location,
    Template,
    EventHitStats,
    CuratedGroup,
    Picture,
    VidlySubmission,
    EventLiveHits,
    Chapter,
)
from airmozilla.search.models import SavedSearch
from airmozilla.surveys.models import Survey, Question, next_question_order
from airmozilla.staticpages.models import StaticPage
from airmozilla.base.tests.test_mozillians import (
    Response,
    GROUPS1,
    GROUPS2,
    VOUCHED_FOR,
    VOUCHED_FOR_USERS,
    NO_USERS,
)
from airmozilla.base.tests.testbase import DjangoTestCase


class TestPages(DjangoTestCase):

    def setUp(self):
        super(TestPages, self).setUp()
        # Make the fixture event live as of the test.
        event = Event.objects.get(title='Test event')
        event.start_time = timezone.now()
        event.archive_time = None
        event.save()

        self.main_channel = Channel.objects.get(
            slug=settings.DEFAULT_CHANNEL_SLUG
        )

    def _calendar_url(
        self,
        privacy,
        location=None,
        channel_slug=None,
        savedsearch=None
    ):
        if channel_slug:
            url = reverse(
                'main:calendar_channel_ical',
                args=(privacy, channel_slug)
            )
        else:
            url = reverse('main:calendar_ical', args=(privacy,))
        if location:
            if isinstance(location, int):
                url += '?location=%s' % location
            else:
                if not isinstance(location, int) and 'name' in location:
                    location = location.name
                url += '?location=%s' % urllib.quote_plus(location)
        if savedsearch:
            url += '?' in url and '&' or '?'
            url += 'ss={}'.format(savedsearch)
        return url

    def test_contribute_json(self):
        response = self.client.get('/contribute.json')
        eq_(response.status_code, 200)
        # Should be valid JSON, but it's a streaming content because
        # it comes from django.views.static.serve
        ok_(json.loads(''.join(response.streaming_content)))
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

        from airmozilla.main.views.pages import can_view_event
        from airmozilla.main.views import is_contributor
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

    def test_view_event_with_unique_title(self):
        event = Event.objects.get(title='Test event')
        url = reverse('main:event', args=(event.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        title_regex = re.compile('<title>([^<]+)')
        og_title_regex = re.compile(
            'property="og:title" content="([^"]+)"'
        )
        title = title_regex.findall(response.content)[0].strip()
        og_title = og_title_regex.findall(response.content)[0].strip()
        eq_(title, event.title + ' | Air Mozilla | Mozilla, in Video')
        eq_(og_title, event.title)

        # create a dupe
        Event.objects.create(
            title=event.title,
            slug='other',
            start_time=timezone.now(),
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        title_2 = title_regex.findall(response.content)[0].strip()
        og_title_2 = og_title_regex.findall(response.content)[0].strip()
        ok_(title != title_2)
        ok_(og_title != og_title_2)
        timestamp = event.location_time.strftime('%d %b %Y')
        ok_(timestamp in title_2)
        ok_(timestamp in og_title_2)

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

        response_empty_page = self.client.get(
            reverse('main:home', kwargs={'page': 10000}))
        eq_(response_empty_page.status_code, 200)

    def test_event(self):
        """Event view page loads correctly if the event is public and
           scheduled and approved; request a login otherwise."""
        event = Event.objects.get(title='Test event')
        group = Group.objects.create(name='testapprover')
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
        # Due to a Heisenbug in the test client, *SOMETIMES* the client
        # loses its sessionstore upon the second request. It only happens
        # some rare times. By doing a fresh new login() again, we
        # drastically reduce the chance of that bug biting us.
        # https://groups.google.com/d/msg/django-users/MRCaRGxRRCQ/mGVcswl7eN4J
        assert self.client.login(username='nigel', password='secret')
        response_ok = self.client.get(event_page)
        eq_(response_ok.status_code, 200)

    def test_view_event_by_event_id(self):
        assert not Event.objects.filter(id=9999).exists()
        url = reverse('main:event', args=('9999',))
        response = self.client.get(url)
        eq_(response.status_code, 404)

        event = Event.objects.get(title='Test event')
        url = reverse('main:event', args=(event.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('<title>{}'.format(event.title) in response.content)

    def test_view_event_channels(self):
        event = Event.objects.get(title='Test event')

        channel1 = Channel.objects.create(
            name='Test Channel1',
            slug='test-channel1')
        channel2 = Channel.objects.create(
            name='Test Channel2',
            slug='test-channel2')

        event.channels.add(channel1)
        event.channels.add(channel2)

        event_url = reverse('main:event', kwargs={'slug': event.slug})
        response = self.client.get(event_url)
        eq_(response.status_code, 200)

        main_channel_url = reverse(
            'main:home_channels',
            args=(self.main_channel.slug,))
        test_channel1_url = reverse(
            'main:home_channels',
            args=(channel1.slug,))
        test_channel2_url = reverse(
            'main:home_channels',
            args=(channel2.slug,))

        ok_(
            self.main_channel.name in response.content and
            main_channel_url in response.content
        )
        ok_(
            'Test Channel1' in response.content and
            test_channel1_url in response.content
        )
        ok_(
            'Test Channel2' in response.content and
            test_channel2_url in response.content
        )

    def test_view_event_with_autoplay(self):
        event = Event.objects.get(title='Test event')
        vidly = Template.objects.create(
            name="Vid.ly HD",
            content=(
                '<iframe src="{{ tag }}?autoplay={{ autoplay }}"></iframe>'
            )
        )
        event.template = vidly
        event.template_environment = {'tag': 'abc123'}
        event.save()
        url = reverse('main:event', kwargs={'slug': event.slug})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('autoplay=false' in response.content)

        response = self.client.get(url, {'autoplay': 'true'})
        eq_(response.status_code, 200)
        ok_('autoplay=true' in response.content)

        response = self.client.get(url, {'autoplay': '1'})
        eq_(response.status_code, 200)
        ok_('autoplay=false' in response.content)

    def test_view_event_with_poster_url_in_template(self):
        event = Event.objects.get(title='Test event')
        template = Template.objects.create(
            name="My Template",
            content=(
                '<video poster="{{ poster_url() }}"></video>'
            )
        )
        event.template = template
        event.template_environment = {}
        event.save()
        url = reverse('main:event', kwargs={'slug': event.slug})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        poster_url = re.findall('<video poster="(.*)">', response.content)[0]
        ok_(poster_url.endswith('.png'))
        ok_(poster_url.startswith(settings.MEDIA_URL))

    def test_event_with_vidly_download_links(self):
        cache.clear()  # we don't want past vidly info cache to affect
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

        ok_(
            'https://vid.ly/abc123?content=video&amp;format=hd_webm'
            not in response.content
        )

        ok_(
            'https://vid.ly/abc123?content=video&amp;format=hd_mp4'
            not in response.content
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
        group = Group.objects.create(name='testapprover')
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
        event = Event.objects.get(title='Test event')
        old_event_slug = EventOldSlug.objects.create(
            event=event,
            slug='test-old-slug',
        )
        response = self.client.get(
            reverse('main:event', kwargs={'slug': old_event_slug.slug})
        )
        self.assertRedirects(
            response,
            reverse('main:event', kwargs={'slug': old_event_slug.event.slug})
        )

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
        event_change = Event.objects.get(title='Test event')
        event_change.title = 'Hello cache clear!'
        event_change.save()
        response_changed = self.client.get(url)
        ok_(response_changed.content != response_public.content)
        ok_('cache clear!' in response_changed.content)

    def test_calendar_ical_filter_by_status(self):
        event = Event.objects.get(title='Test event')
        assert event.status == Event.STATUS_SCHEDULED

        url = self._calendar_url('public')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)

        event.status = Event.STATUS_REMOVED
        event.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' not in response.content)

        event.status = Event.STATUS_PENDING
        event.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' not in response.content)

    def test_calendar_duration(self):
        """Test the behavior of duration in the iCal feed."""
        event = Event.objects.get(title='Test event')
        url = self._calendar_url('public')
        dtend = event.start_time + datetime.timedelta(
            seconds=3600)
        dtend = dtend.strftime("DTEND:%Y%m%dT%H%M%SZ")
        response_public = self.client.get(url)
        ok_(dtend in response_public.content)

        event.duration = 1234
        event.save()
        dtend = event.start_time + datetime.timedelta(
            seconds=1234)
        dtend = dtend.strftime("DTEND:%Y%m%dT%H%M%SZ")
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

    def test_calendar_by_channel(self):

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
            location=event1.location
        )
        event2.channels.add(self.main_channel)
        parent_channel = Channel.objects.create(name='Parent', slug='parent')
        sub_channel = Channel.objects.create(
            name='Sub',
            slug='sub',
            parent=parent_channel,
        )

        url = self._calendar_url('public', channel_slug='xxx')
        response = self.client.get(url)
        eq_(response.status_code, 404)

        url = self._calendar_url('public', channel_slug='main')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)
        ok_('Second test event' in response.content)

        url = self._calendar_url('public', channel_slug='parent')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' not in response.content)
        ok_('Second test event' not in response.content)

        event2.channels.add(sub_channel)
        cache.clear()
        url = self._calendar_url('public', channel_slug='parent')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' not in response.content)
        ok_('Second test event' in response.content)

        url = self._calendar_url('public', channel_slug='sub')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' not in response.content)
        ok_('Second test event' in response.content)

    def test_calendar_by_savedsearch(self):
        event1 = Event.objects.get(title='Test event')
        event2 = Event.objects.create(
            title='Second test event',
            description='Anything',
            start_time=event1.start_time,
            archive_time=event1.archive_time,
            privacy=Event.PRIVACY_PUBLIC,
            status=event1.status,
            placeholder_img=event1.placeholder_img,
            location=event1.location
        )
        channel = Channel.objects.create(name='Channel', slug='channel')
        event2.channels.add(channel)

        savedsearch = SavedSearch.objects.create(
            user=User.objects.create(username='notimportant'),
            filters={
                'title': {
                    'include': 'TEST'
                }
            }
        )

        url = self._calendar_url('public', savedsearch=999999)
        response = self.client.get(url)
        eq_(response.status_code, 404)

        url = self._calendar_url('public', savedsearch=savedsearch.id)
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)
        ok_('Second test event' in response.content)

        # If we change the saved search, it should update the feed
        # automatically.
        savedsearch.filters['title']['include'] = 'SECOND'
        savedsearch.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' not in response.content)
        ok_('Second test event' in response.content)

        # change this back and mess with the channel
        savedsearch.filters['title']['include'] = 'Test'
        savedsearch.filters['channels'] = {'exclude': [channel.id]}
        savedsearch.save()

        response = self.client.get(url)
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
        response_content = response.content.decode('utf-8')
        ok_(url_all in response_content)
        ok_(url_lon in response_content)
        ok_(url_mv in response_content)

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
        response_content = response.content.decode('utf-8')
        ok_(url_all in response_content)
        ok_(url_lon in response_content)
        ok_(url_mv in response_content)

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
        now = timezone.now()
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
            'Google <a href="http://google.com" rel="nofollow">'
            'http://google.com</a>' in
            response.content
        )

        event.additional_links = """
        Google http://google.com\nYahii http://yahii.com
        """.strip()
        event.save()
        response = self.client.get(url)

        ok_(
            'Google <a href="http://google.com" rel="nofollow">'
            'http://google.com</a><br />'
            'Yahii <a href="http://yahii.com" rel="nofollow"'
            '>http://yahii.com</a>'
            in response.content
        )

    def test_call_info_presence(self):
        event = Event.objects.get(title='Test event')
        event.call_info = 'More info'

        url = reverse('main:event', args=(event.slug,))

        event.archive_time = None
        event.start_time = timezone.now() + datetime.timedelta(days=1)
        event.save()
        assert event.is_upcoming()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('More info' in response.content)

        event.start_time = timezone.now()
        event.save()
        assert event.is_live()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('More info' in response.content)

        event.archive_time = timezone.now()
        event.save()
        assert not event.is_live() and not event.is_upcoming()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('More info' not in response.content)

    def test_chapters_tab(self):
        event = Event.objects.get(title='Test event')
        assert not Chapter.objects.filter(event=event)
        url = reverse('main:event', args=(event.slug,))
        edit_url = reverse('main:event_edit_chapters', args=(event.slug,))

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Chapters' not in response.content)

        # if the event has chapters, it should show the tab
        user, = User.objects.all()
        chapter = Chapter.objects.create(
            event=event,
            timestamp=10,
            text='Hi!',
            user=user,
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Chapters' in response.content)
        ok_(edit_url not in response.content)
        chapter.is_active = False
        chapter.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Chapters' not in response.content)

        # but if you're signed in, it should show
        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # Still not, because the event is live!
        ok_('Chapters' not in response.content)

        event.archive_time = timezone.now()
        event.save()
        assert not event.is_live()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_content = response.content.decode('utf-8')
        ok_('Chapters' in response_content)
        ok_(edit_url in response_content)

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
        now = timezone.now()

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
        now = timezone.now()
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
        now = timezone.now()
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

        now = timezone.now()

        channel = Channel.objects.create(
            name='Culture & Context',
            slug='culture-and-context',
            description="""
            <p>The description</p>
            """,
            image='firefox.png',
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

    def test_view_channel_in_reverse_order(self):
        channel = Channel.objects.create(
            name='Culture & Context',
            slug='culture-and-context',
            description="""
            <p>The description</p>
            """,
            image='firefox.png',
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
            response.content.find(two.title) <
            response.content.find(one.title)
        )

        channel.reverse_order = True
        channel.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(one.title in response.content)
        ok_(two.title in response.content)
        ok_(
            response.content.find(one.title) <
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
        now = timezone.now()
        channel = Channel.objects.create(
            name='Culture & Context',
            slug='culture-and-context',
            description="""
            <p>The description</p>
            """,
            image='firefox.png',
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
        now = timezone.now()

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
        StaticPage.objects.create(
            url='sidebar_top_main',
            content='<p>Sidebar Top Main</p>'
        )
        StaticPage.objects.create(
            url='sidebar_bottom_main',
            content='<p>Sidebar Bottom Main</p>'
        )
        StaticPage.objects.create(
            url='sidebar_top_testing',
            content='<p>Sidebar Top Testing</p>'
        )
        StaticPage.objects.create(
            url='sidebar_bottom_testing',
            content='<p>Sidebar Bottom Testing</p>'
        )

        response = self.client.get('/')
        eq_(response.status_code, 200)
        ok_('<p>Sidebar Top Main</p>' in response.content)
        ok_('<p>Sidebar Bottom Main</p>' in response.content)
        ok_('<p>Sidebar Top Testing</p>' not in response.content)
        ok_('<p>Sidebar Bottom Testing</p>' not in response.content)

        Channel.objects.create(
            name='Testing',
            slug='testing',
            description='Anything'
        )
        url = reverse('main:home_channels', args=('testing',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('<p>Sidebar Top Main</p>' not in response.content)
        ok_('<p>Sidebar Bottom Main</p>' not in response.content)
        ok_('<p>Sidebar Top Testing</p>' in response.content)
        ok_('<p>Sidebar Bottom Testing</p>' in response.content)

    def test_sidebar_static_content_all_channels(self):
        # create some flat pages
        StaticPage.objects.create(
            url='sidebar_top_*',
            content='<p>Sidebar Top All</p>'
        )
        response = self.client.get('/')
        eq_(response.status_code, 200)
        ok_('<p>Sidebar Top All</p>' in response.content)

        Channel.objects.create(
            name='Testing',
            slug='testing',
            description='Anything'
        )
        url = reverse('main:home_channels', args=('testing',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('<p>Sidebar Top All</p>' in response.content)

    def test_sidebar_static_content_almost_all_channels(self):
        # create some flat pages
        StaticPage.objects.create(
            url='sidebar_top_*',
            content='<p>Sidebar Top All</p>'
        )
        StaticPage.objects.create(
            url='sidebar_top_testing',
            content='<p>Sidebar Top Testing</p>'
        )
        response = self.client.get('/')
        eq_(response.status_code, 200)
        ok_('<p>Sidebar Top All</p>' in response.content)
        ok_('<p>Sidebar Top Testing</p>' not in response.content)

        Channel.objects.create(
            name='Testing',
            slug='testing',
            description='Anything'
        )
        url = reverse('main:home_channels', args=('testing',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
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

    def test_event_staticpage_fallback(self):
        StaticPage.objects.create(
            url='/test-page',
            title='Flat Test page',
            content='<p>Hi</p>'
        )

        # you can always reach the staticpage by the long URL
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
        # staticpage, the staticpage will have to step aside
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

        def extract_content(content):
            return (
                content.split(
                    'type="application/rss+xml"')[0].split('<link')[-1]
            )

        response = self.client.get(url)
        eq_(response.status_code, 200)
        content = extract_content(response.content)
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
        assert contributor.profile.contributor
        assert self.client.login(username='nigel', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        content = extract_content(response.content)
        ok_(feed_url_anonymous not in content)
        ok_(feed_url_employee not in content)
        ok_(feed_url_contributor in content)

        User.objects.create_user(
            'zandr', 'zandr@mozilla.com', 'secret'
        )
        assert self.client.login(username='zandr', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        content = extract_content(response.content)
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
        event.template.content = "Hello world"
        event.template.save()

        url = reverse('main:event_video', kwargs={'slug': event.slug})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response['X-Frame-Options'], 'ALLOWALL')
        ok_("Not a public event" in response.content)

        # it won't help to be signed in
        user = User.objects.create_user(
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

        # will it help if it's your event?
        event.creator = user
        event.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_("Not a public event" in response.content)

        # no, however if you add ?no-warning which is what the uploader
        # does so you can get a preview in the summary page of YOUR
        # event.
        response = self.client.get(url, {'no-warning': 1})
        eq_(response.status_code, 200)
        eq_(response['X-Frame-Options'], 'ALLOWALL')
        ok_("Not a public event" not in response.content)
        ok_("Hello world" in response.content)

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
        now = timezone.now()
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
            'start': '2015-02-02',
            'end': 'not a number'
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'start': 'not a number',
            'end': '2015-02-02'
        })
        eq_(response.status_code, 400)

        first = datetime.datetime.now()
        while first.day != 1:
            first -= datetime.timedelta(days=1)
        first = first.date()
        last = first
        while last.month == first.month:
            last += datetime.timedelta(days=1)

        first_date = first.strftime('%Y-%m-%d')
        last_date = last.strftime('%Y-%m-%d')

        # start > end
        response = self.client.get(url, {
            'start': last_date,
            'end': first_date
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'start': first_date,
            'end': last_date
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

        test_event.status = Event.STATUS_REMOVED
        test_event.save()
        response = self.client.get(url, {
            'start': first_date,
            'end': last_date
        })
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        ok_(not structure)

    def test_calendar_data_event_duration(self):
        url = reverse('main:calendar_data')
        event = Event.objects.get(title='Test event')
        event.start_time = datetime.datetime(
            2015, 7, 13, 10, 30,
            tzinfo=timezone.utc
        )
        event.estimated_duration = 60 * 30  # half hour
        event.save()

        query = {
            'start': '2015-07-01',
            'end': '2015-07-31'
        }
        response = self.client.get(url, query)
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        event_item, = structure
        assert event_item['title'] == event.title
        fmt = '%Y-%m-%dT%H:%M:%S'
        start = datetime.datetime.strptime(
            event_item['start'].split('+')[0],
            fmt
        )
        end = datetime.datetime.strptime(
            event_item['end'].split('+')[0],
            fmt
        )
        eq_((end - start).seconds, 60 * 30)

        event.duration = 60  # only 1 minute!
        event.save()
        response = self.client.get(url, query)
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        event_item, = structure
        start = datetime.datetime.strptime(
            event_item['start'].split('+')[0],
            fmt
        )
        end = datetime.datetime.strptime(
            event_item['end'].split('+')[0],
            fmt
        )
        # minimum for display on the week/day graph is 20 min
        eq_((end - start).seconds, 60 * 20)

        event.duration = 60 * 37  # 37 minutes
        event.save()
        response = self.client.get(url, query)
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        event_item, = structure
        start = datetime.datetime.strptime(
            event_item['start'].split('+')[0],
            fmt
        )
        end = datetime.datetime.strptime(
            event_item['end'].split('+')[0],
            fmt
        )
        eq_((end - start).seconds, 60 * 37)

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

        first_date = first.strftime('%Y-%m-%d')
        last_date = last.strftime('%Y-%m-%d')

        params = {
            'start': first_date,
            'end': last_date
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
        from airmozilla.main.templatetags.jinja_helpers import short_desc
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
        now = timezone.now()
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
        url = reverse('main:channels')
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
            slug='poisonous',
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

        # use the channels page so that we only get events that appear
        # in the side bar
        url = reverse('main:channels')
        # set up 3 events
        event0 = Event.objects.get(title='Test event')
        now = timezone.now()
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

        calls = []

        def mocked_get(url, **options):
            calls.append(url)
            if 'peterbe' in url:
                if 'group=vip' in url:
                    return Response(NO_USERS)
                else:
                    return Response(VOUCHED_FOR_USERS)
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
        ok_(event.title in smart_text(response.content))

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
    def test_curated_groups_map(self, rget, rlogging):
        # sign in as a member of staff
        User.objects.create_user(
            'gloria', 'gloria@mozilla.com', 'secret'
        )
        assert self.client.login(username='gloria', password='secret')

        event = Event.objects.get(title='Test event')
        url = reverse('main:home')
        event.privacy = Event.PRIVACY_CONTRIBUTORS
        event.save()

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_("Recent Events" in response.content)

        # make it so that viewing the event requires that you're a
        # certain group
        CuratedGroup.objects.create(
            event=event,
            name='vip',
            url='https://mozillians.org/vip',
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(re.findall(
            'This event is available only to staff and Mozilla volunteers '
            'who are members of the\s+vip\s+group.',
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
        ok_(event.title in smart_text(response.content))

        # make it so that viewing the event requires that you're a
        # certain group
        CuratedGroup.objects.create(
            event=event,
            name='vip',
            url='https://mozillians.org/vip',
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.title in smart_text(response.content))

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
        ok_(event.title in smart_text(response.content))

        # but if signed in as a superuser, you can view it
        user.is_superuser = True
        user.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        content = smart_text(response.content)
        ok_('This event is no longer available.' not in content)
        ok_(event.title in content)
        # but there is a flash message warning on the page that says...
        ok_(
            'Event is not publicly visible - not scheduled.'
            in content
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
        now = timezone.now()
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
        eq_(img.attrib['width'], '160')
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
        eq_(img.attrib['width'], '160')
        upcoming_src = img.attrib['src']

        # put the picture back on
        event.picture = picture
        event.save()
        response = self.client.get('/')
        doc = pyquery.PyQuery(response.content)
        img, = doc('aside img')
        upcoming_src_after = img.attrib['src']
        ok_(upcoming_src_after != upcoming_src)

    def test_view_event_without_location(self):
        event = Event.objects.get(title='Test event')
        location = Location.objects.create(
            name='London',
            timezone='Europe/London'
        )
        event.location = location
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        event.start_time = tomorrow
        event.save()

        assert event in Event.objects.upcoming()

        url = reverse('main:event', args=(event.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('London' in response.content)

        location.delete()
        # reload
        event = Event.objects.get(id=event.id)
        ok_(event.location is None)
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('London' not in response.content)
        # the start time will be described in UTC
        ok_(event.start_time.strftime('%H:%M %Z') in response.content)

    def test_view_upcoming_event_without_placeholder_img(self):
        """This is a stupidity fix for
        https://bugzilla.mozilla.org/show_bug.cgi?id=1110004
        where you try to view an *upcoming* event (which doesn't have a
        video) that doesn't have a placeholder_img upload.
        """
        event = Event.objects.get(title='Test event')
        event.archive_time = None
        event.start_time = timezone.now() + datetime.timedelta(days=1)
        event.placeholder_img = None
        with open(self.main_image) as fp:
            picture = Picture.objects.create(file=File(fp))
            event.picture = picture
        event.save()

        event.save()
        assert event in Event.objects.upcoming()

        url = reverse('main:event', args=(event.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

    def test_unpicked_pictures(self):
        event = Event.objects.get(title='Test event')
        event.start_time -= datetime.timedelta(days=1)
        event.archive_time = event.start_time
        event.save()
        assert event in Event.objects.archived()
        assert event.privacy == Event.PRIVACY_PUBLIC
        edit_url = reverse('main:event_edit', args=(event.slug,))
        url = reverse('main:unpicked_pictures')
        response = self.client.get(url)
        # because we're not logged in
        eq_(response.status_code, 302)
        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # but it doesn't appear because it has no pictures
        response_content = response.content.decode('utf-8')
        ok_(edit_url not in response_content)

        with open(self.main_image) as fp:
            picture = Picture.objects.create(
                file=File(fp),
                notes='general picture'
            )
            event.picture = picture
            # but also make a screencap available
            picture2 = Picture.objects.create(
                file=File(fp),
                event=event,
                notes='screencap 1'
            )

        response = self.client.get(url)
        eq_(response.status_code, 200)
        # but it doesn't appear because it has no pictures
        response_content = response.content.decode('utf-8')
        ok_(edit_url in response_content)

        event.picture = picture2
        event.save()
        # now it shouldn't be offered because it already has a picture
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_content = response.content.decode('utf-8')
        ok_(edit_url not in response_content)

    def test_unpicked_pictures_contributor(self):
        event = Event.objects.get(title='Test event')
        event.start_time -= datetime.timedelta(days=1)
        event.archive_time = event.start_time
        event.save()
        assert event in Event.objects.archived()
        assert event.privacy == Event.PRIVACY_PUBLIC
        edit_url = reverse('main:event_edit', args=(event.slug,))
        url = reverse('main:unpicked_pictures')

        with open(self.main_image) as fp:
            # but also make a screencap available
            Picture.objects.create(
                file=File(fp),
                event=event,
                notes='screencap 1'
            )
        user = self._login()
        UserProfile.objects.create(
            user=user,
            contributor=True
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_content = response.content.decode('utf-8')
        ok_(edit_url in response_content)

        # and it should continue to be offered if the event is...
        event.privacy = Event.PRIVACY_CONTRIBUTORS
        event.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_content = response.content.decode('utf-8')
        ok_(edit_url in response_content)

        # but not if it's only company
        event.privacy = Event.PRIVACY_COMPANY
        event.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_content = response.content.decode('utf-8')
        ok_(edit_url not in response_content)  # note the not

    def test_hd_download_links(self):
        event = Event.objects.get(title='Test event')
        vidly = Template.objects.create(
            name="Vid.ly HD",
            content='<iframe src="{{ tag }}"></iframe>'
        )
        event.template = vidly
        event.template_environment = {'tag': 'abc123'}
        event.save()

        vidly_submission = VidlySubmission.objects.create(
            event=event,
            url='https://s3.amazonaws.com/airmozilla/example.mp4',
            tag='abc123',
            hd=True
        )

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

        ok_(
            'https://vid.ly/abc123?content=video&amp;format=hd_webm'
            in response.content
        )

        ok_(
            'https://vid.ly/abc123?content=video&amp;format=hd_mp4'
            in response.content
        )

        vidly_submission.hd = False
        vidly_submission.save()

        response = self.client.get(url)
        eq_(response.status_code, 200)

        ok_(
            'https://vid.ly/abc123?content=video&amp;format=hd_webm'
            not in response.content
        )

        ok_(
            'https://vid.ly/abc123?content=video&amp;format=hd_mp4'
            not in response.content
        )

    @mock.patch('requests.get')
    def test_contributors_page(self, rget):

        calls = []

        def mocked_get(url, **options):
            # This will get used 3 times.
            # 1st time to query for all users in the group.
            # 2nd time to get the details for the first user
            # 3nd time to get the details for the second user
            calls.append(url)

            if '/users/99999' in url:
                return Response(VOUCHED_FOR)

            if '/users/88888' in url:
                result = json.loads(VOUCHED_FOR)
                result['username'] = 'nophoto'
                result['photo']['privacy'] = 'Mozillians'
                result['url'] = result['url'].replace('peterbe', 'nophoto')
                return Response(json.dumps(result))

            if '?group=air+mozilla+contributors' in url:
                # we need to deconstruct the VOUCHED_FOR_USERS fixture
                # and put it together with some dummy data
                result = json.loads(VOUCHED_FOR_USERS)
                results = result['results']
                assert len(results) == 1
                assert results[0]['username'] == 'peterbe'  # know thy fixtures
                cp = copy.copy(results[0])  # deep copy
                cp['username'] = 'nophoto'
                cp['_url'] = cp['_url'].replace('/99999', '/88888')
                results.append(cp)

                assert len(results) == 2
                return Response(json.dumps(result))

            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('main:contributors')
        contributors = (
            'peterbe',
            'nophoto',
            'notfound',
            'notvouched'
        )
        with self.settings(CONTRIBUTORS=contributors):
            response = self.client.get(url)
            eq_(response.status_code, 200)
            ok_(
                'href="https://muzillians.fake/en-US/u/peterbe/"' in
                response.content
            )
            ok_(
                'href="https://muzillians.fake/en-US/u/nophoto/"' not in
                response.content
            )

            assert len(calls) == 3

    def test_event_duration(self):
        event = Event.objects.get(title='Test event')
        event.duration = 3840
        event.save()

        url = reverse('main:event', kwargs={'slug': event.slug})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        assert event.privacy == Event.PRIVACY_PUBLIC

        ok_('Duration: 1 hour 4 minutes' in response.content)

        event.duration = 49
        event.save()

        response = self.client.get(url)
        eq_(response.status_code, 200)

        ok_('Duration: 49 seconds' in response.content)

    def test_executive_summary(self):
        """Note! The Executive Summary page is a very low priority page.
        For example, it's not linked to from any other page.
        Hence, the test is very sparse and just makes sure it renders.
        """
        url = reverse('main:executive_summary')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        response = self.client.get(url, {'start': 'xxx'})
        eq_(response.status_code, 400)

        response = self.client.get(url, {'start': '2015-01-05'})
        eq_(response.status_code, 200)
        ok_('Week of 05 - 11 January 2015' in response.content)
        ok_('"?start=2014-12-29"' in response.content)
        ok_('"?start=2015-01-12"' in response.content)

        # make the subtitle span two different months
        response = self.client.get(url, {'start': '2014-12-29'})
        eq_(response.status_code, 200)
        ok_('Week of 29 December - 04 January 2015' in response.content)

        response = self.client.get(url, {'start': '2015-01-04'})
        # a valid date but not a Monday
        eq_(response.status_code, 400)

    def test_event_livehits(self):

        def get_hits(resp):
            eq_(resp.status_code, 200)
            return json.loads(resp.content)['hits']

        event = Event.objects.get(title='Test event')
        assert event.is_live()
        url = reverse('main:event_livehits', args=(event.id,))
        response = self.client.get(url)
        eq_(get_hits(response), 0)
        # post to it it once
        response = self.client.post(url)
        eq_(get_hits(response), 1)
        eq_(EventLiveHits.objects.get(event=event).total_hits, 1)

        # another get
        response = self.client.get(url)
        eq_(get_hits(response), 1)

        # another push
        response = self.client.post(url)
        eq_(get_hits(response), 1)
        eq_(EventLiveHits.objects.get(event=event).total_hits, 1)

        # change something about our request
        response = self.client.post(url, HTTP_USER_AGENT='Mozilla/Django')
        eq_(get_hits(response), 2)
        eq_(EventLiveHits.objects.get(event=event).total_hits, 2)

        # be signed in
        self._login()
        response = self.client.post(url)
        eq_(get_hits(response), 3)
        eq_(EventLiveHits.objects.get(event=event).total_hits, 3)

        # and a second time as signed in
        response = self.client.post(url)
        eq_(get_hits(response), 3)
        eq_(EventLiveHits.objects.get(event=event).total_hits, 3)

    def test_event_status(self):

        def event_status_url(slug):
            return reverse('main:event_status', args=(slug,))

        event = Event.objects.get(title='Test event')
        response = self.client.get(event_status_url(event.slug))
        eq_(response.status_code, 200)
        eq_(json.loads(response.content)['status'], Event.STATUS_SCHEDULED)

        # change the status and it should be reflected immediately
        event.status = Event.STATUS_PROCESSING
        event.save()
        response = self.client.get(event_status_url(event.slug))
        eq_(response.status_code, 200)
        eq_(json.loads(response.content)['status'], Event.STATUS_PROCESSING)

        response = self.client.get(event_status_url('non-existent-slug',))
        eq_(response.status_code, 404)

    def test_home_with_some_placeholder_images(self):
        e, = Event.objects.live()
        e.archive_time = timezone.now()
        e.save()
        self._attach_file(e, self.main_image)

        with open(self.main_image) as fp:
            Picture.objects.create(
                file=File(fp),
                default_placeholder=True
            )

        # make some copies
        for i in range(15):
            event = Event.objects.create(
                title="Sample Event {0}".format(i + 1),
                slug='slug{0}'.format(i),
                start_time=e.start_time - datetime.timedelta(days=i),
                archive_time=e.start_time - datetime.timedelta(days=i),
                placeholder_img=e.placeholder_img,
                status=e.status,
            )
            for channel in e.channels.all():
                event.channels.add(channel)
        eq_(Event.objects.archived().count(), 15 + 1)

        url = reverse('main:home')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # We show 10 events on the home page
        # The first 4 gets their own picture, the rest get a placeholder
        eq_(len(re.findall('data-layzr="(.*?)"', response.content)), 6)

    def test_browserid_disabled(self):
        with self.settings(BROWSERID_DISABLED=True):
            response = self.client.get('/')
            eq_(response.status_code, 200)
            ok_('Sign in' not in response.content)

            User.objects.create_user(
                'mary', 'mary@mozilla.com', 'secret'
            )
            assert self.client.login(username='mary', password='secret')

            response = self.client.get('/')
            eq_(response.status_code, 200)
            ok_('Sign out' not in response.content)

        response = self.client.get('/')
        eq_(response.status_code, 200)
        ok_('Sign out' in response.content)

        self.client.logout()
        response = self.client.get('/')
        eq_(response.status_code, 200)
        ok_('Sign in' in response.content)

    def test_god_mode(self):
        url = reverse('main:god_mode')
        response = self.client.get(url)
        eq_(response.status_code, 404)

        # first prove that you start signed out
        response = self.client.get('/')
        eq_(response.status_code, 200)
        ok_('Sign out' not in response.content)

        with self.settings(GOD_MODE=True, DEBUG=True):
            response = self.client.get(url)
            eq_(response.status_code, 200)

            User.objects.create_user(
                'mary', 'mary@mozilla.com', 'secret'
            )
            response = self.client.post(url, {'email': 'mary@mozilla.com'})
            eq_(response.status_code, 302)

            response = self.client.get('/')
            eq_(response.status_code, 200)
            ok_('Sign out' in response.content)

    def test_render_event_with_survey(self):
        event = Event.objects.get(title='Test event')
        url = reverse('main:event', args=(event.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # create a survey and add some questions to it
        survey = Survey.objects.create(name='Test', active=True)
        Question.objects.create(
            survey=survey,
            question={
                'question': 'Fav color?',
                'choices': ['Red', 'Green', 'Blue']
            },
            order=next_question_order()
        )
        survey.events.add(event)

        response = self.client.get(url)
        eq_(response.status_code, 200)
        # The question won't be in the event output but the event
        # page will have a reference to the Survey URL
        survey_url = reverse('surveys:load', args=(survey.id,))
        ok_(survey_url in response.content)

        survey.active = False
        survey.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(survey_url not in response.content)

    def test_see_live_unapproved_events(self):
        event = Event.objects.get(title='Test event')
        assert event in Event.objects.live()
        response = self.client.get('/')
        eq_(response.status_code, 200)
        ok_('Streaming Live Now' in response.content)
        ok_(event.title in response.content)

        # make it depend on approval

        group = Group.objects.create(name='testapprover')
        approval = Approval.objects.create(
            event=event,
            group=group
        )
        response = self.client.get('/')
        eq_(response.status_code, 200)
        ok_('Streaming Live Now' not in response.content)
        ok_(event.title not in response.content)

        approval.approved = True
        approval.processed = True
        approval.save()
        response = self.client.get('/')
        eq_(response.status_code, 200)
        ok_('Streaming Live Now' in response.content)
        ok_(event.title in response.content)

        # change it back to un-approved status
        approval.processed = False
        approval.processed = False
        approval.save()
        response = self.client.get('/')
        eq_(response.status_code, 200)
        ok_('Streaming Live Now' not in response.content)
        ok_(event.title not in response.content)
        # but they should appear if logged in
        assert self._login()
        response = self.client.get('/')
        eq_(response.status_code, 200)
        ok_('Streaming Live Now' in response.content)
        ok_(event.title in unicode(response.content, 'utf-8'))

    def test_thumbnails(self):
        event = Event.objects.get(title='Test event')

        url = reverse('main:thumbnails')
        response = self.client.get(url)
        eq_(response.status_code, 400)

        response = self.client.get(url, {'id': event.id})
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'id': event.id,
            'width': 'xxx',
            'height': '90'
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'id': event.id,
            'width': '160',
            'height': '90'
        })
        eq_(response.status_code, 200)
        eq_(json.loads(response.content)['thumbnails'], [])

        # make some pictures for this
        for i in range(4):
            with open(self.main_image) as fp:
                Picture.objects.create(file=File(fp), event=event)

        response = self.client.get(url, {
            'id': event.id,
            'width': '160',
            'height': '90'
        })
        eq_(response.status_code, 200)
        thumbnail_urls = json.loads(response.content)['thumbnails']
        eq_(len(thumbnail_urls), 4)
