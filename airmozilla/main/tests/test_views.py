import datetime
import uuid
import urllib2
import urllib
import httplib

from django.contrib.flatpages.models import FlatPage
from django.contrib.auth.models import Group, User, AnonymousUser
from django.contrib.sites.models import Site
from django.test import TestCase
from django.utils.timezone import utc
from django.conf import settings

from funfactory.urlresolvers import reverse
from nose.tools import eq_, ok_
from mock import patch

from airmozilla.main.models import (
    Approval,
    Event,
    EventOldSlug,
    Participant,
    Tag,
    UserProfile,
    Channel,
    Location
)


class TestPages(TestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']

    def setUp(self):
        # Make the fixture event live as of the test.
        event = Event.objects.get(title='Test event')
        event.start_time = datetime.datetime.utcnow().replace(tzinfo=utc)
        event.archive_time = None
        event.save()

        self.main_channel = Channel.objects.get(
            slug=settings.DEFAULT_CHANNEL_SLUG
        )

    def _calendar_url(self, privacy, location=None):
        url = reverse('main:calendar', args=(privacy,))
        if location:
            if 'name' in location:
                location = location.name
            url += '?location=%s' % urllib.quote_plus(location)
        return url

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

        from airmozilla.main.views import can_view_event
        ok_(can_view_event(event, anonymous))
        ok_(can_view_event(event, contributor))
        ok_(can_view_event(event, employee_wo_profile))
        ok_(can_view_event(event, employee_w_profile))

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

    def test_view_private_events_with_notices(self):
        # for https://bugzilla.mozilla.org/show_bug.cgi?id=821458
        event = Event.objects.get(title='Test event')
        assert event.privacy == Event.PRIVACY_PUBLIC  # default
        event.privacy = Event.PRIVACY_CONTRIBUTORS
        event.save()

        url = reverse('main:event', args=(event.slug,))
        response = self.client.get(url)
        self.assertRedirects(response, reverse('main:login'))

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
        self.assertRedirects(response, reverse('main:login'))

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
        self.assertRedirects(response_fail, reverse('main:login'))
        event.privacy = Event.PRIVACY_CONTRIBUTORS
        event.save()
        response_fail = self.client.get(event_page)
        self.assertRedirects(response_fail, reverse('main:login'))
        event.privacy = Event.PRIVACY_PUBLIC
        event.status = Event.STATUS_INITIATED
        event.save()
        response_fail = self.client.get(event_page)
        eq_(response_fail.status_code, 200)
        ok_('not scheduled' in response_fail.content)

        self.client.logout()
        event.privacy = Event.PRIVACY_COMPANY
        event.status = Event.STATUS_SCHEDULED
        event.save()
        response_fail = self.client.get(event_page)
        self.assertRedirects(response_fail, reverse('main:login'))

        nigel = User.objects.create_user('nigel', 'n@live.in', 'secret')
        UserProfile.objects.create(user=nigel, contributor=True)
        assert self.client.login(username='nigel', password='secret')

        response_fail = self.client.get(event_page)
        self.assertRedirects(response_fail, reverse('main:login'))

        event.privacy = Event.PRIVACY_CONTRIBUTORS
        event.save()
        response_ok = self.client.get(event_page)
        eq_(response_ok.status_code, 200)

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

    def test_calendar(self):
        url = self._calendar_url('public')
        response_public = self.client.get(url)
        eq_(response_public.status_code, 200)
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
        url_lon = self._calendar_url('public', 'London')
        url_mv = self._calendar_url('public', 'Mountain View')
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
        url_lon = self._calendar_url('contributors', 'London')
        url_mv = self._calendar_url('contributors', 'Mountain View')
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
        url_lon = self._calendar_url('company', 'London')
        url_mv = self._calendar_url('company', 'Mountain View')
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
        url_lon = self._calendar_url('public', 'London')
        url_mv = self._calendar_url('public', 'Mountain View')
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

    @patch('airmozilla.manage.vidly.urllib2.urlopen')
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

    @patch('airmozilla.manage.vidly.urllib2.urlopen')
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
        channel_url = reverse('main:home_channels', args=(channel.slug,))
        ok_(channel_url in response.content)
        ok_('0 archived events' in response.content)

        event.privacy = Event.PRIVACY_PUBLIC
        event.save()

        response = self.client.get(reverse('main:channels'))
        eq_(response.status_code, 200)
        ok_('1 archived events' in response.content)

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
        ok_('0 archived events' in response.content)

        event.privacy = Event.PRIVACY_CONTRIBUTORS
        event.save()
        response = self.client.get(reverse('main:channels'))
        eq_(response.status_code, 200)
        ok_('1 archived event' in response.content)

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
        # ...but because it's in the alt text too, multiple by 2
        eq_(response.content.count('Third test event'), 2 * 2)

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
        # featured
        ok_('Third test event' in response.content)
        # upcoming
        ok_('Fourth test event' in response.content)

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
            #assert event in list(Event.objects.archived().all())
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

    def test_featured_but_actively_archived_not_in_sidebar(self):
        # See https://bugzilla.mozilla.org/show_bug.cgi?id=809147
        event = Event.objects.get(title='Test event')
        event.featured = True
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        event.archive_time = now - datetime.timedelta(hours=1)
        event.start_time = now - datetime.timedelta(hours=2)
        event.save()

        # if you go to a static page, the sidebar will be there and
        # show the featured events
        flatpage = FlatPage.objects.create(
            url='/about',
            title='About',
            content='About this page',
        )
        flatpage.sites.add(Site.objects.get(id=settings.SITE_ID))
        response = self.client.get('/about/')
        assert response.status_code == 200, response.status_code
        ok_('Test event' in response.content)
        ok_(
            reverse('main:event', args=(event.slug,))
            in response.content
        )

        # now, let's pretend it's not archived for another hour
        event.archive_time = now + datetime.timedelta(hours=1)
        event.save()
        response = self.client.get('/about/')
        assert response.status_code == 200, response.status_code
        ok_('Test event' not in response.content)

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
