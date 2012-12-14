import datetime
import uuid
import urllib2

from django.contrib.auth.models import Group, User, AnonymousUser
from django.test import TestCase
from django.utils.timezone import utc

from funfactory.urlresolvers import reverse
from nose.tools import eq_, ok_
from mock import patch

from airmozilla.main.models import (
    Approval,
    Event,
    EventOldSlug,
    Participant,
    Tag,
    UserProfile
)


class TestPages(TestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']

    def setUp(self):
        # Make the fixture event live as of the test.
        event = Event.objects.get(title='Test event')
        event.start_time = datetime.datetime.utcnow().replace(tzinfo=utc)
        event.archive_time = None
        event.save()

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
            'This video is restricted to Mozillians and Mozilla employees'
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
            'This video is restricted to Mozilla employees'
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

    def test_calendars(self):
        """Calendars respond successfully."""
        response_public = self.client.get(reverse('main:calendar'))
        eq_(response_public.status_code, 200)
        ok_('LOCATION:Mountain View' in response_public.content)
        response_private = self.client.get(reverse('main:private_calendar'))
        eq_(response_private.status_code, 200)
        # Cache tests
        event_change = Event.objects.get(id=22)
        event_change.title = 'Hello cache clear!'
        event_change.save()
        response_changed = self.client.get(reverse('main:calendar'))
        ok_(response_changed.content != response_public.content)
        ok_('cache clear' in response_changed.content)

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
        response_public = self.client.get(reverse('main:calendar'))
        eq_(response_public.status_code, 200)
        ok_('Check out the Example page' in response_public.content)
        ok_('and THIS PAGE here' in response_public.content)
        ok_('will be truncated' not in response_public.content)

        event.short_description = 'One-liner'
        event.save()
        response_public = self.client.get(reverse('main:calendar'))
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

        Event.objects.create(
            title='Second test event',
            description='Anything',
            start_time=event1.start_time,
            archive_time=event1.archive_time,
            privacy=Event.PRIVACY_COMPANY,  # Note!
            status=event1.status,
            placeholder_img=event1.placeholder_img,
        )

        eq_(Event.objects.approved().count(), 2)
        eq_(Event.objects.archived().count(), 2)

        url = reverse('main:feed', args=('public',))
        response = self.client.get(url)
        ok_('Test event' in response.content)
        ok_('Second test event' not in response.content)

        url = reverse('main:feed')
        response = self.client.get(url)
        ok_('Test event' in response.content)
        ok_('Second test event' in response.content)

        url = reverse('main:feed', args=('private',))
        response = self.client.get(url)
        ok_('Test event' not in response.content)
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

    @patch('airmozilla.base.utils.urllib2.urlopen')
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
