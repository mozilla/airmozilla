import re
import cgi
import datetime
import json
import urllib
import os
import shutil
from cStringIO import StringIO

from nose.tools import eq_, ok_
import mock
import pyquery

from django.conf import settings
from django.contrib.auth.models import User, Group, Permission
from django.core import mail
from django.core.cache import cache
from django.utils import timezone
from django.utils.timezone import utc
from django.core.files import File
from django.core.urlresolvers import reverse

from airmozilla.main.models import (
    Event,
    EventOldSlug,
    Location,
    Template,
    Channel,
    Tag,
    SuggestedEvent,
    SuggestedEventComment,
    VidlySubmission,
    URLMatch,
    URLTransform,
    EventHitStats,
    UserProfile,
    CuratedGroup,
    Picture,
    LocationDefaultEnvironment,
)
from airmozilla.base.tests.test_mozillians import (
    Response,
    GROUPS1,
    GROUPS2
)
from airmozilla.uploads.models import Upload
from airmozilla.comments.models import Discussion
from airmozilla.manage.tests.test_vidly import (
    SAMPLE_XML,
    get_custom_XML,
    SAMPLE_MEDIA_UPDATE_FAILED_XML,
    SAMPLE_MEDIA_UPDATED_XML,
)
from airmozilla.staticpages.models import StaticPage
from airmozilla.manage.views.events import is_privacy_vidly_mismatch
from .base import ManageTestCase


class _Response(object):
    def __init__(self, content, status_code=200):
        self.content = self.text = content
        self.status_code = status_code


class TestEvents(ManageTestCase):
    event_base_data = {
        'status': Event.STATUS_SCHEDULED,
        'description': '...',
        'privacy': 'public',
        'location': '1',
        'channels': '1',
        'tags': 'xxx',
        'template': '1',
        'start_time': '2012-3-4 12:00',
        'estimated_duration': '3600',
    }
    placeholder = 'airmozilla/manage/tests/firefox.png'

    def test_event_request(self):
        """Event request responses and successful creation in the db."""
        response = self.client.get(reverse('manage:event_request'))
        eq_(response.status_code, 200)
        with open(self.placeholder) as fp:
            response_ok = self.client.post(
                reverse('manage:event_request'),
                dict(self.event_base_data, placeholder_img=fp,
                     title='Airmozilla Launch Test')
            )
            response_fail = self.client.post(
                reverse('manage:event_request'),
                {
                    'title': 'Test fails, not enough data!',
                }
            )
            response_cancel = self.client.post(
                reverse('manage:event_request'),
                {
                    'cancel': 'yes'
                }
            )

        self.assertRedirects(response_ok, reverse('manage:events'))
        eq_(response_fail.status_code, 200)
        event = Event.objects.get(title='Airmozilla Launch Test')
        eq_(event.location, Location.objects.get(id=1))
        eq_(event.creator, self.user)
        eq_(response_cancel.status_code, 302)
        self.assertRedirects(response_cancel, reverse('manage:events'))

    def test_event_request_with_approvals(self):
        group1 = Group.objects.create(name='testapprover')
        group2 = Group.objects.create(name='Group2')
        permission = Permission.objects.get(codename='change_approval')
        group1.permissions.add(permission)
        group2.permissions.add(permission)
        group_user = User.objects.create_user(
            'username',
            'em@ail.com',
            'secret'
        )
        group_user.groups.add(group2)

        inactive_user = User.objects.create_user(
            'longgone',
            'long@gone.com',
            'secret'
        )
        inactive_user.is_active = False
        inactive_user.save()
        inactive_user.groups.add(group2)

        long_description_with_html = (
            'The researchers took a "theoretical" approach instead, using '
            'something known as the no-signalling conditions. They '
            'considered an entangled system with a set of independent '
            'physical attributes, some observable, some hidden variables. '
            '\n\n'
            'Next, they allowed the state of the hidden variables '
            'to propagate faster than the speed of light, which let '
            'them influence the measurements on the separated pieces of '
            'the experiment. '
            '\n\n'
            '<ul>'
            '<li>One</li>'
            '<li>Two</li>'
            '</ul>'
            '\n\n'
            'Baskin & Robbins'
        )

        with open(self.placeholder) as fp:
            response = self.client.post(
                reverse('manage:event_request'),
                dict(self.event_base_data,
                     description=long_description_with_html,
                     placeholder_img=fp,
                     title='Airmozilla Launch Test',
                     approvals=[group1.pk, group2.pk])
            )
            eq_(response.status_code, 302)
        event = Event.objects.get(title='Airmozilla Launch Test')
        approvals = event.approval_set.all()
        eq_(approvals.count(), 2)
        # this should send an email to all people in those groups
        email_sent = mail.outbox[-1]
        ok_(group_user.email in email_sent.to)
        ok_(inactive_user.email not in email_sent.to)
        ok_(event.title in email_sent.subject)
        ok_(reverse('manage:approvals') in email_sent.body)
        ok_('Baskin & Robbins' in email_sent.body)
        ok_('<li>One</li>' not in email_sent.body)
        ok_('* One\n' in email_sent.body)
        # edit it and drop the second group
        response_ok = self.client.post(
            reverse('manage:event_edit', kwargs={'id': event.id}),
            dict(self.event_base_data, title='Different title',
                 approvals=[])
        )
        eq_(response_ok.status_code, 302)
        event = Event.objects.get(title='Different title')
        approvals = event.approval_set.all()
        # it's impossible to un-set approvals
        # see https://bugzilla.mozilla.org/show_bug.cgi?id=839024
        eq_(approvals.count(), 2)

    def test_events(self):
        """The events page responds successfully."""
        response = self.client.get(reverse('manage:events'))
        eq_(response.status_code, 200)

    def test_events_with_basic_filtering(self):
        event = Event.objects.get(title='Test event')
        response = self.client.get(reverse('manage:events_data'))
        eq_(response.status_code, 200)
        results = json.loads(response.content)
        eq_(results['events'][0]['id'], event.id)

        event.status = Event.STATUS_PENDING
        event.save()
        response = self.client.get(reverse('manage:events_data'))
        eq_(response.status_code, 200)
        results = json.loads(response.content)
        # still there
        eq_(results['events'][0]['id'], event.id)

        event.status = Event.STATUS_INITIATED
        event.save()
        response = self.client.get(reverse('manage:events_data'))
        eq_(response.status_code, 200)
        results = json.loads(response.content)
        ok_(not results['events'])

    def test_events_with_event_without_location(self):
        event = Event.objects.get(title='Test event')
        response = self.client.get(reverse('manage:events_data'))
        eq_(response.status_code, 200)
        results = json.loads(response.content)
        result = results['events'][0]
        # the "local" time this event starts is 12:30
        ok_('12:30PM' in result['start_time'])
        ok_('21 Jun 2012' in result['start_time'])
        ok_('Mountain View' in result['location'])

        event.location = None
        event.save()
        response = self.client.get(reverse('manage:events_data'))
        eq_(response.status_code, 200)
        results = json.loads(response.content)
        result = results['events'][0]
        ok_('7:30PM' in result['start_time'])
        ok_('21 Jun 2012' in result['start_time'])
        ok_('Mountain View' not in result['location'])

    def test_events_data_with_popcorn(self):
        event = Event.objects.get(title='Test event')
        event.upcoming = False
        event.popcorn_url = 'https://webmaker.org/123'
        event.save()
        response = self.client.get(reverse('manage:events_data'))
        eq_(response.status_code, 200)
        results = json.loads(response.content)
        result = results['events'][0]
        eq_(result['popcorn_url'], event.popcorn_url)

    def test_events_data_with_latest_modify_date(self):
        event = Event.objects.get(title='Test event')
        response = self.client.get(reverse('manage:events_data'))
        eq_(response.status_code, 200)
        results = json.loads(response.content)
        ok_(results['events'])
        eq_(results['max_modified'], event.modified.isoformat())
        first, = results['events']
        eq_(first['modified'], results['max_modified'])

    def test_events_data_since(self):
        url = reverse('manage:events_data')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        results = json.loads(response.content)
        ok_(results['events'])

        response = self.client.get(url, {
            'since': 'junk'
        })
        eq_(response.status_code, 400)

        response = self.client.get(url, {
            'since': results['max_modified']
        })
        eq_(response.status_code, 200)
        results = json.loads(response.content)
        ok_(not results['events'])
        ok_(not results['max_modified'])

        # go back a second in time
        event = Event.objects.get(title='Test event')
        max_modified = event.modified - datetime.timedelta(seconds=1)
        response = self.client.get(url, {
            'since': max_modified,
        })
        eq_(response.status_code, 200)
        results = json.loads(response.content)
        ok_(results['events'])
        eq_(results['max_modified'], event.modified.isoformat())

    def test_events_data_with_pictures_count(self):
        event = Event.objects.get(title='Test event')
        response = self.client.get(reverse('manage:events_data'))
        eq_(response.status_code, 200)
        results = json.loads(response.content)
        result = results['events'][0]
        ok_('pictures' not in result)
        with open(self.placeholder) as fp:
            Picture.objects.create(
                file=File(fp),
                event=event,
            )
        response = self.client.get(reverse('manage:events_data'))
        eq_(response.status_code, 200)
        results = json.loads(response.content)
        result = results['events'][0]
        eq_(result['pictures'], 1)

    def test_events_data_with_has_picture(self):
        event = Event.objects.get(title='Test event')
        response = self.client.get(reverse('manage:events_data'))
        eq_(response.status_code, 200)
        results = json.loads(response.content)
        result = results['events'][0]
        ok_('picture' not in result)
        with open(self.placeholder) as fp:
            picture = Picture.objects.create(
                file=File(fp),
            )
            event.picture = picture
            event.save()
        response = self.client.get(reverse('manage:events_data'))
        eq_(response.status_code, 200)
        results = json.loads(response.content)
        result = results['events'][0]
        eq_(result['picture'], picture.id)

    def test_events_data_with_is_scheduled(self):
        event = Event.objects.get(title='Test event')
        assert event.status == Event.STATUS_SCHEDULED
        response = self.client.get(reverse('manage:events_data'))
        eq_(response.status_code, 200)
        results = json.loads(response.content)
        result = results['events'][0]
        ok_(result['is_scheduled'])

    def test_events_data_with_limit(self):
        event = Event.objects.get(title='Test event')
        Event.objects.create(
            title='Contributors Only Event',
            slug='event2',
            description=event.description,
            start_time=event.start_time,
            privacy=Event.PRIVACY_PUBLIC,
            placeholder_img=event.placeholder_img,
            location=event.location,
            status=Event.STATUS_PENDING,
        )
        Event.objects.create(
            title='MoCo Only Event',
            slug='event3',
            description=event.description,
            start_time=event.start_time,
            privacy=Event.PRIVACY_PUBLIC,
            placeholder_img=event.placeholder_img,
            location=event.location,
            status=Event.STATUS_PENDING,
        )
        url = reverse('manage:events_data')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        result = json.loads(response.content)
        eq_(len(result['events']), 3)

        response = self.client.get(url, {'limit': 2})
        eq_(response.status_code, 200)
        result = json.loads(response.content)
        eq_(len(result['events']), 2)

        response = self.client.get(url, {'limit': -2})
        eq_(response.status_code, 200)
        result = json.loads(response.content)
        eq_(len(result['events']), 3)

    def test_events_data_with_live_and_upcoming(self):
        # some events will be annotated with is_live and is_upcoming
        event = Event.objects.get(title='Test event')
        now = timezone.now()
        event2 = Event.objects.create(
            title='Event 2',
            slug='event2',
            description=event.description,
            start_time=now - datetime.timedelta(minutes=1),
            privacy=Event.PRIVACY_PUBLIC,
            placeholder_img=event.placeholder_img,
            location=event.location,
            status=Event.STATUS_SCHEDULED
        )
        assert not event2.archive_time
        assert event2 in Event.objects.approved()
        assert event2 in Event.objects.live()

        event3 = Event.objects.create(
            title='Event 3',
            slug='event3',
            description=event.description,
            start_time=now + datetime.timedelta(days=1),
            privacy=Event.PRIVACY_PUBLIC,
            placeholder_img=event.placeholder_img,
            location=event.location,
            status=Event.STATUS_SCHEDULED
        )
        assert not event3.archive_time
        assert event3 in Event.objects.approved()
        assert event3 in Event.objects.upcoming()
        assert event3 not in Event.objects.live()

        url = reverse('manage:events_data')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        result = json.loads(response.content)
        titles = [x['title'] for x in result['events']]
        eq_(titles, ['Event 3', 'Event 2', 'Test event'])

        event = result['events'][0]
        ok_(not event.get('is_live'))
        ok_(event['is_upcoming'])

        event = result['events'][1]
        ok_(event['is_live'])
        ok_(not event.get('is_upcoming'))

        event = result['events'][2]
        ok_(not event.get('is_live'))
        ok_(not event.get('is_upcoming'))

    def test_events_data_with_thumbnail(self):
        event = Event.objects.get(title='Test event')
        with open(self.placeholder) as fp:
            response = self.client.post(
                reverse('manage:event_edit', args=(event.pk,)),
                dict(self.event_base_data, placeholder_img=fp,
                     title=event.title)
            )
            eq_(response.status_code, 302)
        url = reverse('manage:events_data')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        result = json.loads(response.content)
        assert result['events'][0]['title'] == event.title

    def test_events_data_without_any_picture(self):
        event = Event.objects.get(title='Test event')
        event.placeholder_img = None
        event.save()
        url = reverse('manage:events_data')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        result = json.loads(response.content)
        ok_(result['events'][0]['nopicture'])

    def test_events_data_pending_with_has_vidly_template(self):
        event = Event.objects.get(title='Test event')
        event.status = Event.STATUS_PENDING
        event.save()

        url = reverse('manage:events_data')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        result = json.loads(response.content)
        row = result['events'][0]
        assert row['title'] == event.title
        ok_(row['is_pending'])
        ok_(not row.get('has_vidly_template'))

        template = event.template
        template.name = 'Vid.ly Fun'
        template.save()
        assert event.has_vidly_template()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        result = json.loads(response.content)
        row = result['events'][0]
        ok_(row['is_pending'])
        ok_(row.get('has_vidly_template'))

    def test_events_seen_by_contributors(self):
        # there should be one event of each level of privacy
        event = Event.objects.get(title='Test event')
        assert event.privacy == Event.PRIVACY_PUBLIC
        event2 = Event.objects.create(
            title='Contributors Only Event',
            slug='event2',
            description=event.description,
            start_time=event.start_time,
            privacy=Event.PRIVACY_CONTRIBUTORS,
            placeholder_img=event.placeholder_img,
            location=event.location,
            status=Event.STATUS_SCHEDULED,
        )
        event3 = Event.objects.create(
            title='MoCo Only Event',
            slug='event3',
            description=event.description,
            start_time=event.start_time,
            privacy=Event.PRIVACY_COMPANY,
            placeholder_img=event.placeholder_img,
            location=event.location,
            status=Event.STATUS_SCHEDULED,
        )
        response = self.client.get(reverse('manage:events_data'))
        eq_(response.status_code, 200)
        result = json.loads(response.content)
        titles = [x['title'] for x in result['events']]
        ok_(event.title in titles)
        ok_(event2.title in titles)
        ok_(event3.title in titles)

        # now log in as a contributor
        contributor = User.objects.create_user(
            'nigel', 'nigel@live.com', 'secret'
        )

        producers = Group.objects.create(name='Producer')
        change_event_permission = Permission.objects.get(
            codename='change_event'
        )
        change_event_others_permission = Permission.objects.get(
            codename='change_event_others'
        )
        producers.permissions.add(change_event_permission)
        producers.permissions.add(change_event_others_permission)
        contributor.groups.add(producers)
        contributor.is_staff = True
        contributor.save()

        UserProfile.objects.create(
            user=contributor,
            contributor=True
        )
        assert self.client.login(username='nigel', password='secret')
        response = self.client.get(reverse('manage:events_data'))
        eq_(response.status_code, 200)
        result = json.loads(response.content)
        titles = [x['title'] for x in result['events']]

        ok_(event.title in titles)
        ok_(event2.title in titles)
        ok_(event3.title not in titles)

        # you can edit the first two events
        edit_url1 = reverse('manage:event_edit', kwargs={'id': event.id})
        response = self.client.get(edit_url1)
        eq_(response.status_code, 200)
        edit_url2 = reverse('manage:event_edit', kwargs={'id': event2.id})
        response = self.client.get(edit_url2)
        eq_(response.status_code, 200)
        edit_url3 = reverse('manage:event_edit', kwargs={'id': event3.id})
        response = self.client.get(edit_url3)
        eq_(response.status_code, 302)

    def test_event_edit_slug(self):
        """Test editing an event - modifying an event's slug
           results in a correct EventOldSlug."""
        event = Event.objects.get(title='Test event')
        response = self.client.get(reverse('manage:event_edit',
                                           kwargs={'id': event.id}))

        eq_(response.status_code, 200)
        response_ok = self.client.post(
            reverse('manage:event_edit', kwargs={'id': event.id}),
            dict(self.event_base_data, title='Tested event')
        )
        self.assertRedirects(response_ok, reverse('manage:events'))
        ok_(EventOldSlug.objects.get(slug='test-event', event=event))
        event = Event.objects.get(title='Tested event')
        eq_(event.slug, 'tested-event')
        eq_(event.modified_user, self.user)
        response_fail = self.client.post(
            reverse('manage:event_edit', kwargs={'id': event.id}),
            {
                'title': 'not nearly enough data',
                'status': Event.STATUS_SCHEDULED
            }
        )
        eq_(response_fail.status_code, 200)

    def test_event_edit_pin(self):
        """Test editing an event - modifying the pin"""
        event = Event.objects.get(title='Test event')
        response = self.client.get(reverse('manage:event_edit',
                                           kwargs={'id': event.id}))

        eq_(response.status_code, 200)
        ok_('Pin' in response.content)

        response = self.client.post(
            reverse('manage:event_edit', kwargs={'id': event.id}),
            dict(
                self.event_base_data,
                title='Tested event',
                pin='1'
            )
        )
        eq_(response.status_code, 200)
        ok_('Pin too short' in response.content)

        response = self.client.post(
            reverse('manage:event_edit', kwargs={'id': event.id}),
            dict(self.event_base_data, title='Tested event',
                 pin='12345')
        )
        self.assertRedirects(response, reverse('manage:events'))
        ok_(Event.objects.get(pin='12345'))

    def test_event_edit_unset_location(self):
        """Test editing an event - modifying the pin"""
        event = Event.objects.get(title='Test event')
        assert event.location.timezone == 'US/Pacific'
        assert event.start_time.hour == 19
        assert event.start_time.minute == 30
        assert event.start_time.tzinfo == utc

        url = reverse('manage:event_edit', kwargs={'id': event.id})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # the event's start_time is 19:30 in UTC,
        # which is 12:30 in US/Pacific
        ok_('12:30' in response.content)

        # now, set the location to None
        response = self.client.post(
            url,
            dict(self.event_base_data, title='Test event',
                 location='',
                 start_time=event.start_time.strftime('%Y-%m-%d %H:%M'))
        )
        eq_(response.status_code, 302)

        event = Event.objects.get(title='Test event')
        # the start time should not have changed
        assert event.start_time.hour == 19
        assert event.start_time.minute == 30
        assert event.start_time.tzinfo == utc

        response = self.client.get(url)
        eq_(response.status_code, 200)
        # now, because no timezone is known, we have to rely on UTC
        ok_('12:30' not in response.content)
        ok_('19:30' in response.content)

    def test_event_edit_templates(self):
        """Event editing results in correct template environments."""
        event = Event.objects.get(title='Test event')
        url = reverse('manage:event_edit', kwargs={'id': event.id})
        response_ok = self.client.post(
            url,
            dict(self.event_base_data, title='template edit',
                 template_environment='tv1=\'hi\'\ntv2===')
        )
        self.assertRedirects(response_ok, reverse('manage:events'))
        event = Event.objects.get(id=event.id)
        eq_(event.template_environment, {'tv1': "'hi'", 'tv2': '=='})
        response_edit_page = self.client.get(url)
        eq_(response_edit_page.status_code, 200,
            'Edit page renders OK with a specified template environment.')
        response_fail = self.client.post(
            url,
            dict(self.event_base_data, title='template edit',
                 template_environment='failenvironment')
        )
        eq_(response_fail.status_code, 200)

    def test_event_archive(self):
        """Event archive page loads and shows correct archive_time behavior."""
        event = Event.objects.get(title='Test event')
        event.archive_time = None
        # also, make it non-public
        event.privacy = Event.PRIVACY_COMPANY
        event.save()
        url = reverse('manage:event_archive', kwargs={'id': event.id})
        response_ok = self.client.get(url)
        eq_(response_ok.status_code, 200)
        # the `token_protection` should be forced on
        ok_('Required for non-public events' in response_ok.content)

        response_ok = self.client.post(url)
        self.assertRedirects(response_ok, reverse('manage:events'))
        event_modified = Event.objects.get(id=event.id)
        eq_(event_modified.status, Event.STATUS_SCHEDULED)
        now = timezone.now()
        ok_(
            abs(event_modified.archive_time - now) <=
            datetime.timedelta(1)
        )

    def test_event_archive_with_default_archive_template(self):
        """If you have a template that has `default_archive_template` True
        then it should mention that on the event archive page."""
        event = Event.objects.get(title='Test event')
        event.archive_time = None
        # also, make it non-public
        event.privacy = Event.PRIVACY_COMPANY
        event.save()
        url = reverse('manage:event_archive', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        assert not Template.objects.filter(default_archive_template=True)
        ok_('default_archive_template' not in response.content)
        template = Template.objects.create(
            name='Foo',
            default_archive_template=True
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('default_archive_template' in response.content)
        ok_('value="%s"' % template.pk in response.content)

    def test_event_archive_with_upload(self):
        """event archive an event that came from a suggested event that has
        a file upload."""
        event = Event.objects.get(title='Test event')
        event.archive_time = None
        event.save()

        upload = Upload.objects.create(
            user=self.user,
            url='http://s3.com/some.flv',
            size=12345
        )

        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        location = Location.objects.get(id=1)
        SuggestedEvent.objects.create(
            user=self.user,
            title='TITLE',
            slug='SLUG',
            short_description='SHORT DESCRIPTION',
            description='DESCRIPTION',
            start_time=tomorrow,
            location=location,
            placeholder_img=self.placeholder,
            privacy=Event.PRIVACY_CONTRIBUTORS,
            first_submitted=now,
            accepted=event,
            upload=upload
        )

        url = reverse('manage:event_archive', kwargs={'id': event.id})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('http://s3.com/some.flv' in response.content)

    def test_event_archive_with_vidly_template(self):
        """Event archive page loads and shows correct archive_time behavior."""
        vidly_template = Template.objects.create(name='Vid.ly HD')

        event = Event.objects.get(title='Test event')
        event.archive_time = None
        event.save()

        url = reverse('manage:event_archive', kwargs={'id': event.id})
        response_ok = self.client.post(url, {
            'template': vidly_template.pk,
            'template_environment': 'tag=abc123',
        })
        self.assertRedirects(response_ok, reverse('manage:events'))
        event_modified = Event.objects.get(id=event.id)
        eq_(event_modified.archive_time, None)
        eq_(event_modified.status, Event.STATUS_PENDING)

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_event_archive_with_vidly_template_with_vidly_submission(
        self, p_urllib2
    ):
        """Event archive an event with a tag that has a VidlySubmission
        that was successful. If you do that it should immediately
        set an archive_time."""

        def mocked_urlopen(request):
            return StringIO(get_custom_XML(tag='abc123'))

        p_urllib2.urlopen = mocked_urlopen

        vidly_template = Template.objects.create(name='Vid.ly HD')
        event = Event.objects.get(title='Test event')
        event.archive_time = None
        assert event.status == Event.STATUS_SCHEDULED
        event.save()

        VidlySubmission.objects.create(
            event=event,
            url='https://aws.com/file.mov',
            tag='abc123',
        )

        url = reverse('manage:event_archive', kwargs={'id': event.id})
        response_ok = self.client.post(url, {
            'template': vidly_template.pk,
            'template_environment': 'tag=abc123',
        })
        self.assertRedirects(response_ok, reverse('manage:events'))
        event_modified = Event.objects.get(id=event.id)
        eq_(event_modified.status, Event.STATUS_SCHEDULED)
        ok_(event_modified.archive_time)

    def test_event_duplication(self):
        event = Event.objects.get(title='Test event')
        url = reverse('manage:event_duplicate', args=(event.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('value="Test event"' in response.content)
        ok_(
            'value="%s"' % event.location_time.strftime('%Y-%m-%d %H:%M')
            in response.content
        )

    def test_event_duplication_without_location(self):
        event = Event.objects.get(title='Test event')
        event.location = None
        event.save()
        url = reverse('manage:event_duplicate', args=(event.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('value="Test event"' in response.content)
        ok_(
            'value="%s"' % event.start_time.strftime('%Y-%m-%d %H:%M')
            in response.content
        )

    def test_event_duplication_with_discussion(self):
        event = Event.objects.get(title='Test event')
        discussion = Discussion.objects.create(
            event=event,
            enabled=True,
            closed=False,
            notify_all=True,
            moderate_all=True
        )
        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        discussion.moderators.add(bob)

        url = reverse('manage:event_duplicate', args=(event.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        data = {
            'title': 'Different',
            'description': event.description,
            'short_description': event.short_description,
            'location': event.location.pk,
            'privacy': event.privacy,
            'status': event.status,
            'start_time': event.start_time.strftime('%Y-%m-%d %H:%M'),
            'estimated_duration': event.estimated_duration,
            'channels': [x.pk for x in event.channels.all()],
            'enable_discussion': True,
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)

        new_discussion = Discussion.objects.get(
            event__title='Different'
        )
        eq_(new_discussion.notify_all, True)
        eq_(new_discussion.moderate_all, True)
        eq_(
            list(new_discussion.moderators.all()),
            list(discussion.moderators.all())
        )

    @mock.patch('requests.get')
    def test_event_duplication_with_curated_groups(self, rget):

        def mocked_get(url, **options):
            if '/v2/groups/' in url and 'name=badasses' in url:
                return Response(json.dumps({
                    "count": 1,
                    "results": [
                        {
                            "url": "http://muzillians.org/group/1",
                            "_url": "http://muzillians.org/api/group/1",
                            "id": "1000",
                            "name": "badasses",
                            "member_count": 1,
                            "next": "should not be necessary",
                        }
                    ]
                }))
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        event = Event.objects.get(title='Test event')
        CuratedGroup.objects.create(
            event=event,
            name='badasses'
        )
        url = reverse('manage:event_duplicate', args=(event.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('value="badasses"' in response.content)

        data = {
            'title': 'Different',
            'description': event.description,
            'short_description': event.short_description,
            'location': event.location.pk,
            'privacy': event.privacy,
            'status': event.status,
            'start_time': event.start_time.strftime('%Y-%m-%d %H:%M'),
            'estimated_duration': event.estimated_duration,
            'channels': [x.pk for x in event.channels.all()],
            'enable_discussion': True,
            'curated_groups': ['badasses'],
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        # this is expected to exist
        ok_(CuratedGroup.objects.get(event__title='Different'))

        cache.clear()

    def test_event_duplication_with_picture(self):
        event = Event.objects.get(title='Test event')
        with open(self.placeholder) as fp:
            picture = Picture.objects.create(file=File(fp))
            event.picture = picture
            event.placeholder_img = None
            event.save()

        url = reverse('manage:event_duplicate', args=(event.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        data = {
            'title': 'Different',
            'description': event.description,
            'short_description': event.short_description,
            'location': event.location.pk,
            'privacy': event.privacy,
            'status': event.status,
            'start_time': event.start_time.strftime('%Y-%m-%d %H:%M'),
            'estimated_duration': event.estimated_duration,
            'channels': [x.pk for x in event.channels.all()],
            'enable_discussion': True,
            'picture': picture.id,
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        event = Event.objects.get(title='Different')
        eq_(event.picture, picture)

    def test_event_duplication_custom_channels(self):
        ch = Channel.objects.create(
            name='Custom Culture',
            slug='custom-culture'
        )
        event = Event.objects.get(title='Test event')
        event.channels.filter(slug=settings.DEFAULT_CHANNEL_SLUG).delete()
        event.channels.add(ch)
        event.save()

        url = reverse('manage:event_duplicate', args=(event.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('value="Test event"' in response.content)
        # expect a <option> tag selected with this name
        tags = re.findall(
            '<option (.*?)>([\w\s]+)</option>',
            response.content,
            flags=re.M
        )
        for attrs, value in tags:
            if value == ch.name:
                ok_('selected' in attrs)

    def test_event_preview_shortcut(self):
        # become anonymous (reverse what setUp() does)
        self.client.logout()

        # view it anonymously
        event = Event.objects.get(title='Test event')
        url = reverse('main:event', args=(event.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        edit_url = reverse('manage:event_edit', args=(event.pk,))
        ok_(edit_url not in response.content)
        # now log in
        assert self.client.login(username='fake', password='fake')
        # check that you can view the edit page
        response = self.client.get(edit_url)
        eq_(response.status_code, 200)
        # and now the real test
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_content = response.content.decode('utf-8')
        ok_(edit_url in response_content)

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_vidly_url_to_shortcode(self, p_urllib2):
        event = Event.objects.get(title='Test event')
        assert event.privacy == Event.PRIVACY_PUBLIC
        url = reverse('manage:vidly_url_to_shortcode', args=(event.pk,))

        def mocked_urlopen(request):
            return StringIO("""
            <?xml version="1.0"?>
            <Response>
              <Message>All medias have been added.</Message>
              <MessageCode>2.1</MessageCode>
              <BatchID>47520</BatchID>
              <Success>
                <MediaShortLink>
                  <SourceFile>http://www.com/file.flv</SourceFile>
                  <ShortLink>8oxv6x</ShortLink>
                  <MediaID>13969839</MediaID>
                  <QRCode>http://vid.ly/8oxv6x/qrcodeimg</QRCode>
                  <HtmlEmbed>code code</HtmlEmbed>
                  <EmailEmbed>more code code</EmailEmbed>
                </MediaShortLink>
              </Success>
            </Response>
            """)
        p_urllib2.urlopen = mocked_urlopen

        response = self.client.get(url)
        eq_(response.status_code, 405)

        response = self.client.post(url, {
            'url': 'not a url'
        })
        eq_(response.status_code, 400)

        match = URLMatch.objects.create(
            name='Always Be Safe',
            string='^http://'
        )
        URLTransform.objects.create(
            match=match,
            find='^http://',
            replace_with='https://'
        )
        response = self.client.post(url, {
            'url': 'http://www.com/'
        })
        eq_(response.status_code, 200)
        content = json.loads(response.content)
        eq_(content['shortcode'], '8oxv6x')
        eq_(content['url'], 'https://www.com/')

        arguments = list(p_urllib2.Request.mock_calls[0])[1]
        # the first argument is the URL
        ok_('vid.ly' in arguments[0])
        # the second argument is querystring containing the XML used
        data = cgi.parse_qs(arguments[1])
        xml = data['xml'][0]
        ok_('<HD>YES</HD>' not in xml)
        ok_('<HD>NO</HD>' in xml)
        ok_('<SourceFile>https://www.com/</SourceFile>' in xml)

        # re-fetch it
        match = URLMatch.objects.get(pk=match.pk)
        eq_(match.use_count, 1)

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_vidly_url_to_shortcode_with_forced_protection(self, p_urllib2):
        event = Event.objects.get(title='Test event')
        event.privacy = Event.PRIVACY_COMPANY
        event.save()
        url = reverse('manage:vidly_url_to_shortcode', args=(event.pk,))

        def mocked_urlopen(request):
            return StringIO("""
            <?xml version="1.0"?>
            <Response>
              <Message>All medias have been added.</Message>
              <MessageCode>2.1</MessageCode>
              <BatchID>47520</BatchID>
              <Success>
                <MediaShortLink>
                  <SourceFile>http://www.com/file.flv</SourceFile>
                  <ShortLink>8oxv6x</ShortLink>
                  <MediaID>13969839</MediaID>
                  <QRCode>http://vid.ly/8oxv6x/qrcodeimg</QRCode>
                  <HtmlEmbed>code code</HtmlEmbed>
                  <EmailEmbed>more code code</EmailEmbed>
                </MediaShortLink>
              </Success>
            </Response>
            """)
        p_urllib2.urlopen = mocked_urlopen

        response = self.client.post(url, {
            'url': 'http://www.com/'
        })
        eq_(response.status_code, 200)
        content = json.loads(response.content)
        eq_(content['shortcode'], '8oxv6x')

        submission, = VidlySubmission.objects.all()
        ok_(submission.token_protection)
        ok_(not submission.hd)

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_vidly_url_to_shortcode_with_hd(self, p_urllib2):
        event = Event.objects.get(title='Test event')
        url = reverse('manage:vidly_url_to_shortcode', args=(event.pk,))

        def mocked_urlopen(request):
            return StringIO("""
            <?xml version="1.0"?>
            <Response>
              <Message>All medias have been added.</Message>
              <MessageCode>2.1</MessageCode>
              <BatchID>47520</BatchID>
              <Success>
                <MediaShortLink>
                  <SourceFile>http://www.com/file.flv</SourceFile>
                  <ShortLink>8oxv6x</ShortLink>
                  <MediaID>13969839</MediaID>
                  <QRCode>http://vid.ly/8oxv6x/qrcodeimg</QRCode>
                  <HtmlEmbed>code code</HtmlEmbed>
                  <EmailEmbed>more code code</EmailEmbed>
                </MediaShortLink>
              </Success>
            </Response>
            """)
        p_urllib2.urlopen = mocked_urlopen

        response = self.client.post(url, {
            'url': 'http://www.com/',
            'hd': True,
        })
        eq_(response.status_code, 200)
        content = json.loads(response.content)
        eq_(content['shortcode'], '8oxv6x')

        arguments = list(p_urllib2.Request.mock_calls[0])[1]
        # the first argument is the URL
        ok_('vid.ly' in arguments[0])
        # the second argument is querystring containing the XML used
        data = cgi.parse_qs(arguments[1])
        xml = data['xml'][0]
        ok_('<HD>YES</HD>' in xml)
        ok_('<HD>NO</HD>' not in xml)

    def test_events_autocomplete(self):
        event = Event.objects.get(title='Test event')
        event2 = Event.objects.create(
            title='The Other Cool Title Event',
            description=event.description,
            start_time=event.start_time,
        )
        eq_(Event.objects.all().count(), 2)
        url = reverse('manage:event_autocomplete')

        response = self.client.get(url)
        eq_(response.status_code, 400)

        response = self.client.get(url, {'q': 'something', 'max': 'nan'})
        eq_(response.status_code, 400)

        response = self.client.get(url, {'q': 'eVEnt'})
        eq_(response.status_code, 200)
        content = json.loads(response.content)
        eq_(content, ['Test event', 'The Other Cool Title Event'])

        response = self.client.get(url, {'q': 'EVen', 'max': 1})
        eq_(response.status_code, 200)
        content = json.loads(response.content)
        eq_(content, ['Test event'])

        response = self.client.get(url, {'q': 'E'})
        eq_(response.status_code, 200)
        content = json.loads(response.content)
        eq_(content, [])

        response = self.client.get(url, {'q': 'COOL'})
        eq_(response.status_code, 200)
        content = json.loads(response.content)
        eq_(content, ['The Other Cool Title Event'])

        response = self.client.get(url, {'q': 'COO'})
        eq_(response.status_code, 200)
        content = json.loads(response.content)
        eq_(content, ['The Other Cool Title Event'])

        response = self.client.get(url, {'q': 'THE'})
        eq_(response.status_code, 200)
        content = json.loads(response.content)
        eq_(content, [])

        # the autocomplete caches the same search
        event2.title = event2.title.replace('Cool', 'Brilliant')
        event2.save()

        response = self.client.get(url, {'q': 'COol'})
        eq_(response.status_code, 200)
        content = json.loads(response.content)
        eq_(content, ['The Other Cool Title Event'])

        # but if the query is different it should work
        response = self.client.get(url, {'q': 'brill'})
        eq_(response.status_code, 200)
        content = json.loads(response.content)
        eq_(content, ['The Other Brilliant Title Event'])

    def test_overwrite_old_slug(self):
        # you create an event, change the slug and change it back
        with open(self.placeholder) as fp:
            response = self.client.post(
                reverse('manage:event_request'),
                dict(self.event_base_data, placeholder_img=fp,
                     title='Launch')
            )
            eq_(response.status_code, 302)
        event = Event.objects.get(slug='launch')
        url = reverse('main:event', args=('launch',))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # now edit the slug
        response = self.client.post(
            reverse('manage:event_edit', kwargs={'id': event.pk}),
            dict(self.event_base_data,
                 title='Different title',
                 slug='different',)
        )
        eq_(response.status_code, 302)
        assert Event.objects.get(slug='different')

        old_url = url
        url = reverse('main:event', args=('different',))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        response = self.client.get(old_url)
        eq_(response.status_code, 302)
        self.assertRedirects(response, url)

        # but suppose we change our mind back
        response = self.client.post(
            reverse('manage:event_edit', kwargs={'id': event.pk}),
            dict(self.event_base_data,
                 title='Launch title',
                 slug='launch',)
        )
        eq_(response.status_code, 302)
        event = Event.objects.get(slug='launch')

        old_url = url
        url = reverse('main:event', args=('launch',))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        response = self.client.get(old_url)
        eq_(response.status_code, 302)
        self.assertRedirects(response, url)

        event.delete()
        response = self.client.get(url)
        eq_(response.status_code, 404)

        response = self.client.get(old_url)
        eq_(response.status_code, 404)

    def test_overwrite_old_slug_twice(self):
        # based on https://bugzilla.mozilla.org/show_bug.cgi?id=850742#c3
        with open(self.placeholder) as fp:
            response = self.client.post(
                reverse('manage:event_request'),
                dict(self.event_base_data, placeholder_img=fp,
                     title='Champagne')
            )
            eq_(response.status_code, 302)
        event = Event.objects.get(slug='champagne')
        # now edit the slug
        response = self.client.post(
            reverse('manage:event_edit', kwargs={'id': event.pk}),
            dict(self.event_base_data,
                 title=event.title,
                 slug='somethingelse')
        )

        # back again
        response = self.client.post(
            reverse('manage:event_edit', kwargs={'id': event.pk}),
            dict(self.event_base_data,
                 title=event.title,
                 slug='champagne')
        )

        # one last time
        response = self.client.post(
            reverse('manage:event_edit', kwargs={'id': event.pk}),
            dict(self.event_base_data,
                 title=event.title,
                 slug='somethingelse')
        )

        url = reverse('main:event', args=('somethingelse',))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        old_url = reverse('main:event', args=('champagne',))
        response = self.client.get(old_url)
        eq_(response.status_code, 302)
        self.assertRedirects(response, url)

    def test_editing_event_without_location(self):
        # Edit an event that doesn't have a location, and keep it that way.
        # It should not affect the start_time.
        event = Event.objects.get(title='Test event')
        event.location = None
        event.save()
        start_time_before = event.start_time
        url = reverse('manage:event_edit', args=(event.id,))
        response = self.client.post(url, {
            'title': event.title,
            'description': event.description,
            'short_description': event.short_description,
            'location': '',
            'status': event.status,
            'slug': event.slug,
            'start_time': event.start_time.strftime('%Y-%m-%d %H:%M'),
            'channels': [x.id for x in event.channels.all()],
            'tags': [x.id for x in event.tags.all()],
            'estimated_duration': event.estimated_duration,
            'privacy': event.privacy,
        })
        eq_(response.status_code, 302)

        # reload and check the start_time
        event = Event.objects.get(id=event.id)
        start_time_after = event.start_time
        eq_(start_time_before, start_time_after)

    def test_editing_event_tags(self):
        # you create an event, edit the tags and mix the case
        with open(self.placeholder) as fp:
            response = self.client.post(
                reverse('manage:event_request'),
                dict(self.event_base_data, placeholder_img=fp,
                     title='Launch')
            )
            eq_(response.status_code, 302)
        event = Event.objects.get(slug='launch')
        # now edit the tags
        response = self.client.post(
            reverse('manage:event_edit', kwargs={'id': event.pk}),
            dict(self.event_base_data,
                 title=event.title,
                 tags=['One', 'Two'])
        )
        eq_(response.status_code, 302)
        event = Event.objects.get(pk=event.pk)

        ok_(Tag.objects.get(name='One') in list(event.tags.all()))
        ok_(Tag.objects.get(name='Two') in list(event.tags.all()))

        # Edit a tag that already exists
        Tag.objects.create(name='three')
        count_tags_before = Tag.objects.all().count()
        response = self.client.post(
            reverse('manage:event_edit', kwargs={'id': event.pk}),
            dict(self.event_base_data,
                 title=event.title,
                 tags=['One', 'Two', 'THREE'])
        )
        count_tags_after = Tag.objects.all().count()
        eq_(count_tags_before, count_tags_after)

    def test_event_request_with_clashing_staticpage(self):
        StaticPage.objects.create(
            url='/egg-plants/',
            title='Egg Plants',
        )
        with open(self.placeholder) as fp:
            response = self.client.post(
                reverse('manage:event_request'),
                dict(self.event_base_data, placeholder_img=fp,
                     title='Egg Plants')
            )
            eq_(response.status_code, 200)
            ok_('Form errors' in response.content)

    def test_event_edit_with_clashing_staticpage(self):
        # if you edit the event and its slug already clashes with a
        # StaticPage, there's little we can do, the StaticPage was added
        # after
        with open(self.placeholder) as fp:
            response = self.client.post(
                reverse('manage:event_request'),
                dict(self.event_base_data, placeholder_img=fp,
                     title='Champagne')
            )
            eq_(response.status_code, 302)

        StaticPage.objects.create(
            url='/egg-plants/',
            title='Egg Plants',
        )

        event = Event.objects.get(slug='champagne')
        # now edit the event without changing the slug
        response = self.client.post(
            reverse('manage:event_edit', kwargs={'id': event.pk}),
            dict(self.event_base_data,
                 title="New Title",
                 slug=event.slug)
        )
        # should be ok
        eq_(response.status_code, 302)

        response = self.client.post(
            reverse('manage:event_edit', kwargs={'id': event.pk}),
            dict(self.event_base_data,
                 title="New Title",
                 slug='egg-plants')
        )
        # should NOT be ok
        eq_(response.status_code, 200)
        ok_('Form errors' in response.content)

    def test_event_edit_with_vidly_submissions(self):
        event = Event.objects.get(title='Test event')
        url = reverse('manage:event_edit', args=(event.pk,))

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('id="vidly-submission"' not in response.content)

        template = event.template
        template.name = 'Vid.ly Fun'
        template.save()

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('id="vidly-submission"' in response.content)

        VidlySubmission.objects.create(
            event=event,
            url='http://www.file',
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('1 Vid.ly Submission' in response.content)

        # a second one
        VidlySubmission.objects.create(
            event=event,
            url='http://www.file.different.file',
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('2 Vid.ly Submissions' in response.content)

        submissions_url = reverse(
            'manage:event_vidly_submissions',
            args=(event.pk,)
        )
        ok_(submissions_url in response.content)

    @mock.patch('urllib2.urlopen')
    def test_event_edit_with_stuck_pending(self, p_urlopen):

        def mocked_urlopen(request):
            return StringIO(SAMPLE_XML.strip())

        p_urlopen.side_effect = mocked_urlopen

        event = Event.objects.get(title='Test event')
        event.template_environment = {'tag': 'abc123'}
        event.status = Event.STATUS_PENDING
        event.save()

        url = reverse('manage:event_edit', args=(event.pk,))

        template = event.template
        template.name = 'Vid.ly Fun'
        template.save()
        submission = VidlySubmission.objects.create(
            event=event,
            url='http://www.file',
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('1 Vid.ly Submission' in response.content)

        auto_archive_url = reverse(
            'manage:event_archive_auto',
            args=(event.pk,)
        )
        ok_(auto_archive_url not in response.content)
        # the reason it's not there is because the VidlySubmission
        # was made very recently.
        # It will appear if the VidlySubmission does not exist
        submission.submission_time -= datetime.timedelta(hours=1)
        submission.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(auto_archive_url in response.content)

        # or if there is no VidlySubmission at all
        submission.delete()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(auto_archive_url in response.content)

        response = self.client.post(auto_archive_url)
        eq_(response.status_code, 302)
        event = Event.objects.get(pk=event.pk)
        eq_(event.status, Event.STATUS_SCHEDULED)
        ok_(event.archive_time)

    def test_event_vidly_submissions(self):
        event = Event.objects.get(title='Test event')
        template = event.template
        template.name = 'Vid.ly Fun'
        template.save()

        url = reverse('manage:event_vidly_submissions', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # add one
        VidlySubmission.objects.create(
            event=event,
            url='http://something.long/url.file',
            hd=True,
            token_protection=False,
            tag='abc123',
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('http://something.long/url.file' in response.content)
        ok_('abc123' in response.content)

    def test_event_vidly_submissions_with_active_submission(self):
        event = Event.objects.get(title='Test event')
        template = event.template
        template.name = 'Vid.ly Fun'
        template.save()
        # add one
        submission = VidlySubmission.objects.create(
            event=event,
            url='http://something.long/url.file',
            hd=True,
            token_protection=False,
            tag='abc123',
        )
        assert 'Vid.ly' in event.template.name
        event.template_environment = {'tag': 'abc123'}
        event.save()

        url = reverse('manage:event_vidly_submissions', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Actively used' in response.content)

        # If you have a submission with token_protection and the event
        # is public, you'll get a warning message.
        submission.token_protection = True
        submission.save()
        assert event.privacy == Event.PRIVACY_PUBLIC
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Warning!' in response.content)

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_delete_event_vidly_submissions(self, p_urllib2):

        def mocked_urlopen(request):
            return StringIO("""
            <?xml version="1.0"?>
            <Response>
              <Message>Success</Message>
              <MessageCode>0.0</MessageCode>
              <Success>
                <MediaShortLink>abc456</MediaShortLink>
              </Success>
              <Errors>
                <Error>
                  <SourceFile>http://www.com</SourceFile>
                  <ErrorCode>1</ErrorCode>
                  <Description>ErrorDescriptionK</Description>
                  <Suggestion>ErrorSuggestionK</Suggestion>
                </Error>
              </Errors>
            </Response>
            """)

        p_urllib2.urlopen = mocked_urlopen

        event = Event.objects.get(title='Test event')
        template = event.template
        template.name = 'Vid.ly Fun'
        template.save()
        event.template_environment = {'tag': 'abc123'}
        event.save()

        url = reverse('manage:event_vidly_submissions', args=(event.pk,))

        # add one
        vs1 = VidlySubmission.objects.create(
            event=event,
            url='http://something.long/url.file',
            hd=True,
            token_protection=False,
            tag='abc123',
        )
        vs2 = VidlySubmission.objects.create(
            event=event,
            url='http://something.long/url2.file',
            hd=True,
            token_protection=False,
            tag='abc456',
        )
        vs3 = VidlySubmission.objects.create(
            event=event,
            url='http://something.long/url2.file.broken',
            hd=True,
            token_protection=False,
            tag='xyz987',
        )
        response = self.client.post(url, {'id': [vs1.id, vs2.id, vs3.id]})
        # because we're not allowed to delete vs1
        eq_(response.status_code, 400)

        response = self.client.post(url, {'id': [vs2.id, vs3.id]})
        eq_(response.status_code, 302)
        ok_(VidlySubmission.objects.filter(tag='abc123'))
        ok_(not VidlySubmission.objects.filter(tag='abc456'))
        # because it couldn't be deleted, we don't delete the record
        ok_(VidlySubmission.objects.filter(tag='xyz987'))

        # this time, do it by force
        response = self.client.post(url, {'id': [vs3.id], 'forced': 1})
        eq_(response.status_code, 302)
        ok_(VidlySubmission.objects.filter(tag='abc123'))
        ok_(not VidlySubmission.objects.filter(tag='xyz987'))

    def test_delete_event_vidly_submissions_wo_tag(self):

        event = Event.objects.get(title='Test event')
        template = event.template
        template.name = 'Vid.ly Fun'
        template.save()
        event.template_environment = {'tag': 'abc123'}
        event.save()

        submission = VidlySubmission.objects.create(
            event=event,
            url='http://something.long/url.file',
            hd=True,
            token_protection=False,
            tag=None,
        )
        url = reverse('manage:event_vidly_submissions', args=(event.pk,))
        response = self.client.post(url, {'id': [submission.id]})
        eq_(response.status_code, 302)
        # but it wouldn't be deleted
        ok_(VidlySubmission.objects.get(id=submission.id))

        response = self.client.post(
            url,
            {'id': [submission.id], 'forced': True}
        )
        eq_(response.status_code, 302)
        ok_(not VidlySubmission.objects.filter(id=submission.id))

    def test_event_vidly_submission(self):
        event = Event.objects.get(title='Test event')
        submission = VidlySubmission.objects.create(
            event=event,
            url='http://something.long/url.file',
            hd=True,
            token_protection=False,
            tag='abc123',
            submission_error='Something went wrong',
        )
        url = reverse(
            'manage:event_vidly_submission',
            args=(event.pk, submission.pk)
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['submission_error'], 'Something went wrong')

        # or as fields
        response = self.client.get(url, {'as_fields': True})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        ok_(data['fields'])
        first_field = data['fields'][0]
        ok_('key' in first_field)
        ok_('value' in first_field)

    def test_event_hit_stats(self):
        event = Event.objects.get(title='Test event')
        now = timezone.now()
        event.start_time = now - datetime.timedelta(days=400)
        event.archive_time = now - datetime.timedelta(days=365)
        event.save()

        EventHitStats.objects.create(
            event=event,
            total_hits=101,
            shortcode='abc123',
        )

        url = reverse('manage:event_hit_stats')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # 101 / 365 days ~= 0.3
        ok_(u'1\xa0year' in unicode(response.content, 'utf-8'))
        ok_('101' in response.content)
        ok_('0.3' in response.content)

    def test_event_hit_stats_include_excluded(self):
        event = Event.objects.get(title='Test event')
        poison = Channel.objects.create(
            name='Poison',
            exclude_from_trending=True
        )
        event.channels.add(poison)

        now = timezone.now()
        event.start_time = now - datetime.timedelta(days=400)
        event.archive_time = now - datetime.timedelta(days=365)
        event.save()

        EventHitStats.objects.create(
            event=event,
            total_hits=101,
            shortcode='abc123',
        )

        url = reverse('manage:event_hit_stats')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.title not in response.content)

        response = self.client.get(url, {'include_excluded': True})
        eq_(response.status_code, 200)
        ok_(event.title in unicode(response.content, 'utf-8'))

    def test_event_hit_stats_archived_today(self):
        event = Event.objects.get(title='Test event')
        now = timezone.now()
        event.start_time = now
        event.archive_time = now
        event.save()

        EventHitStats.objects.create(
            event=event,
            total_hits=1,
            shortcode='abc123',
        )

        url = reverse('manage:event_hit_stats')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.title not in response.content)

    def test_hit_statistics_with_filter(self):
        event = Event.objects.get(slug='test-event')
        event_hit = Event.objects.create(
            title='Test event hit',
            slug='test-event-hit',
            description=event.description,
            privacy=Event.PRIVACY_PUBLIC,
            placeholder_img=event.placeholder_img,
            location=event.location,
            start_time='2012-06-22T19:30:00Z',
            archive_time='2012-06-22T20:00:00Z',
        )

        EventHitStats.objects.create(
            event=event,
            total_hits=101,
            shortcode='abc123',
        )

        EventHitStats.objects.create(
            event=event_hit,
            total_hits=102,
            shortcode='abc456',
        )

        response = self.client.get(
            reverse('manage:event_hit_stats'),
            {
                'title': event_hit.title,
            }
        )
        eq_(response.status_code, 200)

        view_url_event = reverse('main:event', args=(event.slug,))
        view_url_event_hit = reverse('main:event', args=(event_hit.slug,))
        response_content = response.content.decode('utf-8')
        eq_(response_content.count(view_url_event_hit), 1)
        eq_(response_content.count(view_url_event), 0)

    def test_event_edit_without_vidly_template(self):
        """based on https://bugzilla.mozilla.org/show_bug.cgi?id=879725"""
        event = Event.objects.get(title='Test event')
        event.status = Event.STATUS_PENDING
        event.archive_time = None
        event.template = None
        event.save()

        url = reverse('manage:event_edit', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

    def test_event_edit_with_suggested_event_comments(self):
        event = Event.objects.get(title='Test event')
        now = timezone.now()
        suggested_event = SuggestedEvent.objects.create(
            user=self.user,
            title=event.title,
            slug=event.slug,
            description=event.description,
            short_description=event.short_description,
            location=event.location,
            start_time=event.start_time,
            accepted=event,
            submitted=now,
        )
        SuggestedEventComment.objects.create(
            suggested_event=suggested_event,
            user=self.user,
            comment='hi!\n"friend"'
        )
        url = reverse('manage:event_edit', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(
            'Additional comments from original requested event'
            in response.content
        )
        ok_('hi!<br />&quot;friend&quot;' in response.content)

    def test_event_edit_of_retracted_submitted_event(self):
        event = Event.objects.get(title='Test event')
        now = timezone.now()
        suggested_event = SuggestedEvent.objects.create(
            user=self.user,
            title=event.title,
            slug=event.slug,
            description=event.description,
            short_description=event.short_description,
            location=event.location,
            start_time=event.start_time,
            accepted=event,
            submitted=now,
        )
        url = reverse('manage:event_edit', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        suggested_event.submitted = None
        suggested_event.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)

    def test_event_location_time_create_and_edit(self):
        """test that the input can be local time but the event is stored in
        UTC"""
        paris = Location.objects.create(
            name='Paris',
            timezone='Europe/Paris'
        )
        with open(self.placeholder) as fp:
            data = dict(
                self.event_base_data,
                placeholder_img=fp,
                title='In Paris!',
                start_time='2013-09-25 10:00',
                location=paris.pk,
            )
            response = self.client.post(
                reverse('manage:event_request'),
                data
            )
            eq_(response.status_code, 302)
        event = Event.objects.get(title='In Paris!')
        eq_(event.start_time.tzinfo, utc)
        eq_(event.start_time.hour, 8)

        url = reverse('manage:event_edit', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # expect the Paris location to be pre-selected
        ok_(
            '<option value="%s" selected="selected">Paris</option>' % paris.pk
            in response.content
        )
        start_time_tag = re.findall(
            '<input.*?id="id_start_time".*?>',
            response.content
        )[0]
        # expect to see the location time in there instead
        ok_('10:00' in start_time_tag, start_time_tag)

        # suppose now we want to make the event start at 13:00 in Paris
        response = self.client.post(
            url,
            dict(
                self.event_base_data,
                location=paris.pk,
                start_time='2013-09-25 13:00',
                title='Different Now'
            ),
        )
        eq_(response.status_code, 302)
        event = Event.objects.get(title='Different Now')
        eq_(event.start_time.tzinfo, utc)
        eq_(event.start_time.hour, 11)

        # pull up the edit one more time
        response = self.client.get(url)
        eq_(response.status_code, 200)
        start_time_tag = re.findall(
            '<input.*?id="id_start_time".*?>',
            response.content
        )[0]
        # expect to see the location time in there instead
        ok_('13:00' in start_time_tag, start_time_tag)

    @mock.patch('logging.error')
    @mock.patch('requests.get')
    def test_editing_event_curated_groups(self, rget, rlogging):

        def mocked_get(url, **options):
            if '/v2/groups/' in url and 'page=2' in url:
                return Response(GROUPS2)
            if '/v2/groups/' in url:
                return Response(GROUPS1)
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        event = Event.objects.get(title='Test event')
        url = reverse('manage:event_edit', args=(event.pk,))

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Curated groups' in response.content)
        response = self.client.post(
            url,
            dict(
                self.event_base_data,
                title=event.title,
                curated_groups=['Group 1', 'Group 2'],
            )
        )
        eq_(response.status_code, 302)
        ok_(CuratedGroup.objects.get(event=event, name='Group 1'))
        ok_(CuratedGroup.objects.get(event=event, name='Group 2'))

        # edit it again
        response = self.client.post(
            url,
            dict(
                self.event_base_data,
                title=event.title,
                curated_groups=['Group 1', 'Group X'],
            )
        )
        eq_(response.status_code, 302)
        ok_(CuratedGroup.objects.get(event=event, name='Group 1'))
        ok_(CuratedGroup.objects.get(event=event, name='Group X'))
        ok_(not CuratedGroup.objects.filter(event=event, name='Group 2'))

        # because fetching groups is cached
        cache.clear()

    def test_event_upload(self):
        event = Event.objects.get(title='Test event')
        # there needs to exist a template which is the
        # `default_archive_template` one
        template, = Template.objects.all()
        template.default_archive_template = True
        template.save()

        url = reverse('manage:event_upload', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # if the event has a file upload, you'd expect to see a link to it here
        upload = Upload.objects.create(
            user=self.user,
            url='https://aws.com/file.foo',
            file_name='file.foo',
            size=123456,
            event=event,
        )
        event.upload = upload
        event.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('file.foo' in response.content)

    def test_event_upload_automation_details(self):
        """When you go to the event upload there are details embedded in
        the page that is used by the javascript automation steps (which
        are quite complex).
        Here we just want to test that all those details are there as
        expected.
        """
        event = Event.objects.get(title='Test event')
        # there needs to exist a template which is the
        # `default_archive_template` one
        template, = Template.objects.all()
        template.default_archive_template = True
        template.content = """
        <iframe src="{{ key }}"></iframe>
        """
        template.save()

        url = reverse('manage:event_upload', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        doc = pyquery.PyQuery(response.content)
        element, = doc('form#upload')
        eq_(
            element.attrib['data-vidly-shortcut-url'],
            reverse('manage:vidly_url_to_shortcode', args=(event.id,))
        )
        eq_(
            element.attrib['data-event-archive-url'],
            reverse('manage:event_archive', args=(event.id,))
        )
        eq_(
            json.loads(element.attrib['data-vidly-submit-details']),
            {
                'email': self.user.email,
                'hd': True,
                'token_protection': False
            }
        )
        assert event.privacy == Event.PRIVACY_PUBLIC
        eq_(
            json.loads(element.attrib['data-event-archive-details']),
            {
                'template': template.id,
                'shortcode_key_name': 'key'
            }
        )

    def test_event_transcript(self):
        event = Event.objects.get(title='Test event')
        event.transcript = "Some content"
        event.save()

        url = reverse('manage:event_transcript', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Some content' in response.content)

        response = self.client.post(url, {'transcript': 'New content'})
        eq_(response.status_code, 302)
        event = Event.objects.get(pk=event.pk)
        eq_(event.transcript, 'New content')

    @mock.patch('requests.get')
    def test_event_transcript_scraping(self, rget):

        def mocked_get(url, **options):
            eq_(
                url,
                'https://etherpad.mozilla.org/ep/pad/export/foo-bar/latest?'
                'format=txt'
            )
            return _Response(
                "Content here",
                200
            )

        rget.side_effect = mocked_get

        event = Event.objects.get(title='Test event')
        event.additional_links = """
        https://etherpad.mozilla.org/foo-bar
        """
        event.save()

        url = reverse('manage:event_transcript', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('https://etherpad.mozilla.org/foo-bar' in response.content)

        response = self.client.get(url, {
            'urls': ['https://etherpad.mozilla.org/foo-bar']
        })
        eq_(response.status_code, 200)
        ok_('Content here' in response.content)

    @mock.patch('requests.get')
    def test_event_transcript_scraping_not_working(self, rget):

        def mocked_get(url, **options):
            eq_(
                url,
                'https://etherpad.mozilla.org/ep/pad/export/foo-bar/latest?'
                'format=txt'
            )
            return _Response(
                None,
                500
            )

        rget.side_effect = mocked_get

        event = Event.objects.get(title='Test event')
        event.additional_links = """
        https://etherpad.mozilla.org/foo-bar
        """
        event.save()
        url = reverse('manage:event_transcript', args=(event.pk,))
        response = self.client.get(url, {
            'urls': ['https://etherpad.mozilla.org/foo-bar']
        })
        eq_(response.status_code, 200)
        ok_('Some things could not be scraped correctly')

    def test_stop_live_event(self):
        event = Event.objects.get(title='Test event')
        assert event in Event.objects.approved()
        event.archive_time = None
        now = timezone.now()
        nowish = now - datetime.timedelta(minutes=1)
        event.start_time = nowish
        event.save()
        assert event in Event.objects.live()

        # there needs to exist a template which is the
        # `default_archive_template` one
        template, = Template.objects.all()
        template.default_archive_template = True
        template.save()

        edit_url = reverse('manage:event_edit', args=(event.pk,))
        response = self.client.get(edit_url)
        eq_(response.status_code, 200)
        url = reverse('manage:stop_live_event', args=(event.pk,))
        ok_(url in response.content)

        # let's click it
        response = self.client.post(url)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('manage:event_upload', args=(event.pk,))
        )

        # reload the event and it should have changed status
        event = Event.objects.get(pk=event.pk)
        eq_(event.status, Event.STATUS_PROCESSING)

    def test_event_redirect_thumbnail(self):
        event = Event.objects.get(title='Test event')
        with open(self.placeholder) as fp:
            event.placeholder_img = File(fp)
            event.save()

        assert event.placeholder_img

        url = reverse('manage:redirect_event_thumbnail', args=(event.id,))
        response = self.client.get(url)
        eq_(response.status_code, 302)
        thumbnail_url = response['Location']
        ok_(settings.MEDIA_URL in thumbnail_url)

    def test_event_edit_with_hit_statistics(self):
        event = Event.objects.get(title='Test event')
        url = reverse('manage:event_edit', args=(event.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Archived hits:' not in response.content)

        event.template_environment = {'tag': 'abc123'}
        event.save()

        EventHitStats.objects.create(
            event=event,
            total_hits=1234,
            shortcode=event.template_environment['tag']
        )

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Archived hits:' in response.content)
        ok_('1,234' in response.content)

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_is_privacy_vidly_mismatch(self, p_urllib2):

        def mocked_urlopen(request):
            xml_string = get_custom_XML(tag='abc123')
            assert '<Private>false</Private>'
            return StringIO(xml_string)

        p_urllib2.urlopen = mocked_urlopen

        event = Event.objects.get(title='Test event')
        event.template = None
        event.template_environment = {}
        event.save()
        # no template associated with event
        ok_(not is_privacy_vidly_mismatch(event))

        event.template = Template.objects.create(name='Nothing', content='x')
        event.save()
        # template not named Vid.ly something
        ok_(not is_privacy_vidly_mismatch(event))

        event.template.name = 'Vid.LY Something'
        event.template.save()
        # no template_environment['tag']
        ok_(not is_privacy_vidly_mismatch(event))

        event.template_environment['tag'] = 'abc123'
        event.save()
        assert event.privacy == Event.PRIVACY_PUBLIC, event.privacy
        # doesn't mismatch fixture
        ok_(not is_privacy_vidly_mismatch(event))

        event.privacy = Event.PRIVACY_COMPANY
        event.save()
        # finally a mismatch!
        ok_(is_privacy_vidly_mismatch(event))

    @mock.patch('airmozilla.manage.vidly.urllib2.urlopen')
    def test_event_edit_with_privacy_vidly_mismatch(self, p_urlopen):

        def mocked_urlopen(request):
            xml_sent = urllib.unquote_plus(request.data)
            if 'UpdateMedia' in xml_sent:
                xml_string = SAMPLE_MEDIA_UPDATED_XML
            else:
                xml_string = get_custom_XML(tag='abc123')
                # it's just a query
                assert '<Private>false</Private>'
            return StringIO(xml_string)

        p_urlopen.side_effect = mocked_urlopen

        vidly_template = Template.objects.create(
            name='Vid.ly Something',
            content=''
        )
        event = Event.objects.get(title='Test event')
        assert event.privacy == Event.PRIVACY_PUBLIC

        # let's make sure there is a VidlySubmission of this too
        submission = VidlySubmission.objects.create(
            tag='abc123',
            event=event,
            url='https://s3.com',
            token_protection=False
        )

        with open(self.placeholder) as fp:
            response = self.client.post(
                reverse('manage:event_edit', args=(event.pk,)),
                dict(self.event_base_data, placeholder_img=fp,
                     title=event.title,
                     template=vidly_template.id,
                     template_environment="tag=abc123",
                     privacy=Event.PRIVACY_COMPANY)
            )
            eq_(response.status_code, 302)

        # reload the submission
        submission = VidlySubmission.objects.get(id=submission.id)
        ok_(submission.token_protection)

    @mock.patch('airmozilla.manage.vidly.urllib2.urlopen')
    def test_event_edit_with_privacy_vidly_mismatch_error(self, p_urlopen):

        def mocked_urlopen(request):
            xml_sent = urllib.unquote_plus(request.data)
            if 'UpdateMedia' in xml_sent:
                xml_string = SAMPLE_MEDIA_UPDATE_FAILED_XML
            else:
                xml_string = get_custom_XML(tag='abc123')
                # it's just a query
                assert '<Private>false</Private>'
            return StringIO(xml_string)

        p_urlopen.side_effect = mocked_urlopen

        vidly_template = Template.objects.create(
            name='Vid.ly Something',
            content=''
        )
        event = Event.objects.get(title='Test event')
        assert event.privacy == Event.PRIVACY_PUBLIC

        # let's make sure there is a VidlySubmission of this too
        submission = VidlySubmission.objects.create(
            tag='abc123',
            event=event,
            url='https://s3.com',
            token_protection=False
        )

        with open(self.placeholder) as fp:
            response = self.client.post(
                reverse('manage:event_edit', args=(event.pk,)),
                dict(self.event_base_data, placeholder_img=fp,
                     title=event.title,
                     template=vidly_template.id,
                     template_environment="tag=abc123",
                     privacy=Event.PRIVACY_COMPANY)
            )
            # Note that even though the UpdateMedia failed,
            # it still goes ahead with the redirect.
            eq_(response.status_code, 302)

        # reload the submission
        submission = VidlySubmission.objects.get(id=submission.id)
        # it should not have changed
        ok_(not submission.token_protection)

    def test_is_template_environment_mismatch(self):
        event = Event.objects.get(title='Test event')

        url = reverse(
            'manage:event_template_environment_mismatch',
            args=(event.id,)
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), None)

        assert event.location
        assert event.template
        event.template_environment = {
            'foo': 'bar'
        }
        event.save()

        LocationDefaultEnvironment.objects.create(
            location=event.location,
            template=event.template,
            privacy=event.privacy,
            template_environment={
                'something': 'different',
            }
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(
            json.loads(response.content)['url'],
            reverse('manage:location_edit', args=(event.location.id,))
        )

        # we can now post here
        response = self.client.post(url)
        eq_(response.status_code, 302)
        # reload
        event = Event.objects.get(id=event.id)
        eq_(
            event.template_environment,
            {
                'something': 'different',
            }
        )

    def test_edit_event_archive_time(self):
        event = Event.objects.get(title='Test event')
        url = reverse('manage:event_archive_time', args=(event.id,))
        assert event.archive_time
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.get_status_display() in response.content)
        # the input converts the time to the local timezone of
        ok_(
            event.archive_time.strftime('%Y-%m-%d %H:%M:%S') in
            response.content
        )
        response = self.client.post(url, {
            'archive_time': ''
        })
        eq_(response.status_code, 302)
        event = Event.objects.get(id=event.id)
        eq_(event.archive_time, None)

        response = self.client.post(url, {
            'archive_time': '2015-04-01 12:00:00'
        })
        eq_(response.status_code, 302)
        event = Event.objects.get(id=event.id)
        dt = datetime.datetime(2015, 4, 1, 12, 0, 0)
        dt = dt.replace(tzinfo=utc)
        eq_(event.archive_time, dt)

    @mock.patch('airmozilla.manage.views.events.boto.connect_s3')
    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_event_delete(self, p_urllib2, mocked_connect_s3):

        assert not Upload.objects.all()
        assert not VidlySubmission.objects.all()
        assert not Picture.objects.all()

        def mocked_urlopen(request):
            return StringIO("""
            <?xml version="1.0"?>
            <Response>
              <Message>Success</Message>
              <MessageCode>0.0</MessageCode>
              <Success>
                <MediaShortLink>8oxv6x</MediaShortLink>
              </Success>
              <Errors>
                <Error>
                  <SourceFile>http://www.com</SourceFile>
                  <ErrorCode>1</ErrorCode>
                  <Description>ErrorDescriptionK</Description>
                  <Suggestion>ErrorSuggestionK</Suggestion>
                </Error>
              </Errors>
            </Response>
            """)

        sent_xml_strings = []

        def mocked_Request(url, data, **kwargs):
            sent_xml_strings.append(urllib.unquote_plus(data))
            return mock.MagicMock()

        p_urllib2.Request = mocked_Request
        p_urllib2.urlopen = mocked_urlopen

        event = Event.objects.get(title='Test event')
        url = reverse('manage:event_delete', args=(event.id,))
        response = self.client.post(url)
        # because the event is not in state of removed
        eq_(response.status_code, 404)
        event.status = Event.STATUS_REMOVED
        event.save()

        # create some uploads
        Upload.objects.create(
            user=self.user,
            event=event,
            url='http://aws.com/file1.mov',
            size=98765
        )
        Upload.objects.create(
            user=self.user,
            event=event,
            url='http://aws.com/file2.mov',
            size=123456
        )

        # create some vidly submissions
        VidlySubmission.objects.create(
            event=event,
            tag='abc123',
        )
        VidlySubmission.objects.create(
            event=event,
            tag='xyz987',
        )

        # Create some pictures
        file_paths = []
        for i in range(3):
            with open(self.placeholder) as fp:
                picture = Picture.objects.create(
                    event=event,
                    file=File(fp),
                    notes=str(i)
                )
                assert os.path.isfile(picture.file.path)
                file_paths.append(picture.file.path)
        # associate the event with the last picture
        event.picture = picture
        event.save()

        # finally, try to delete it again
        response = self.client.post(url)
        eq_(response.status_code, 302)

        mocked_connect_s3().get_bucket.assert_called_once_with(
            settings.S3_UPLOAD_BUCKET
        )
        mocked_connect_s3().get_bucket().delete_key.assert_any_call(
            '/file2.mov'
        )
        mocked_connect_s3().get_bucket().delete_key.assert_any_call(
            '/file1.mov'
        )

        eq_(len(sent_xml_strings), 2)
        ok_('<Action>DeleteMedia</Action>' in sent_xml_strings[0])
        ok_('<Action>DeleteMedia</Action>' in sent_xml_strings[1])
        ok_('<MediaShortLink>xyz987</MediaShortLink>' in sent_xml_strings[0])
        ok_('<MediaShortLink>abc123</MediaShortLink>' in sent_xml_strings[1])

        for file_path in file_paths:
            ok_(not os.path.isfile(file_path))

        # We can do this because there weren't any of these before the
        # test started.
        ok_(not Upload.objects.all())
        ok_(not VidlySubmission.objects.all())
        ok_(not Picture.objects.all())

    @mock.patch('requests.head')
    @mock.patch('subprocess.Popen')
    def test_event_fetch_duration(self, mock_popen, rhead):

        ffmpeged_urls = []

        def mocked_popen(command, **kwargs):
            url = destination = None
            if command[1] == '-i':
                # doing a fetch info
                url = command[2]
            elif command[1] == '-ss':
                # screen capturing
                destination = command[-1]
                assert os.path.isdir(os.path.dirname(destination))
            else:
                raise NotImplementedError(command)

            ffmpeged_urls.append(url)

            # sample_jpg = self.sample_jpg

            class Inner:
                def communicate(self):
                    out = err = ''
                    if url is not None:
                        if 'some.flv' in url:
                            err = """
                Duration: 00:00:11.01, start: 0.000000, bitrate: 1076 kb/s
                            """
                        else:
                            raise NotImplementedError(url)
                    # elif destination is not None:
                    #     shutil.copyfile(sample_jpg, destination)
                    else:
                        raise NotImplementedError()
                    return out, err

            return Inner()

        mock_popen.side_effect = mocked_popen

        def mocked_head(url, **options):
            return Response(
                '',
                200
            )

        rhead.side_effect = mocked_head

        event = Event.objects.get(title='Test event')
        assert not event.duration
        url = reverse('manage:event_fetch_duration', args=(event.id,))
        eq_(self.client.get(url).status_code, 405)
        response = self.client.post(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), {'duration': None})

        event.upload = Upload.objects.create(
            user=self.user,
            url='http://s3domaincom/some.flv',
            size=12345
        )
        event.save()
        response = self.client.post(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), {'duration': 11})
        event = Event.objects.get(id=event.id)
        eq_(event.duration, 11)

        eq_(len(ffmpeged_urls), 1)

        # hit it a second time
        response = self.client.post(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), {'duration': 11})
        eq_(len(ffmpeged_urls), 1)

    @mock.patch('requests.head')
    @mock.patch('subprocess.Popen')
    def test_event_fetch_screencaptures(self, mock_popen, rhead):

        ffmpeged_urls = []

        def mocked_popen(command, **kwargs):
            url = destination = None
            if command[1] == '-ss':
                # screen capturing
                destination = command[-1]
                assert os.path.isdir(os.path.dirname(destination))
            else:
                raise NotImplementedError(command)

            ffmpeged_urls.append(url)

            sample_jpg = 'airmozilla/manage/tests/presenting.jpg'

            class Inner:
                def communicate(self):
                    out = err = ''
                    if destination is not None:
                        shutil.copyfile(sample_jpg, destination)
                    else:
                        raise NotImplementedError()
                    return out, err

            return Inner()

        mock_popen.side_effect = mocked_popen

        def mocked_head(url, **options):
            return Response(
                '',
                200
            )

        rhead.side_effect = mocked_head

        event = Event.objects.get(title='Test event')
        assert not event.duration
        url = reverse('manage:event_fetch_screencaptures', args=(event.id,))
        eq_(self.client.get(url).status_code, 405)
        response = self.client.post(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), {'pictures': 0})

        event.upload = Upload.objects.create(
            user=self.user,
            url='http://s3domaincom/some.flv',
            size=12345
        )
        event.save()
        response = self.client.post(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), {'pictures': 0})

        event.duration = 12
        event.save()
        response = self.client.post(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), {
            'pictures': settings.SCREENCAPTURES_NO_PICTURES
        })
        assert Picture.objects.filter(event=event).count()
        eq_(len(ffmpeged_urls), settings.SCREENCAPTURES_NO_PICTURES)

        # hit it a second time
        response = self.client.post(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), {
            'pictures': settings.SCREENCAPTURES_NO_PICTURES
        })
        eq_(len(ffmpeged_urls), settings.SCREENCAPTURES_NO_PICTURES)

    @mock.patch('subprocess.Popen')
    @mock.patch('requests.head')
    def test_event_edit_duration(self, rhead, rpopen):

        def mocked_head(url, **options):
            return Response(
                '',
                200
            )

        rhead.side_effect = mocked_head

        def mocked_popen(command, **kwargs):
            url = command[2]

            class Inner:
                def communicate(self):
                    out = ''
                    if 'xyz123' in url:
                        err = """
            Duration: 00:05:20.47, start: 0.000000, bitrate: 1076 kb/s
                        """
                    else:
                        raise NotImplementedError(url)
                    return out, err

            return Inner()

        rpopen.side_effect = mocked_popen

        event = Event.objects.get(title='Test event')
        event.duration = 120
        event.template_environment = {'tag': 'xyz123'}
        event.save()
        event.template.name = 'Vid.ly Whatever'
        event.template.save()
        url = reverse('manage:event_edit_duration', args=(event.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('2 minutes' in response.content)
        # let's change it to something else
        response = self.client.post(url, {'duration': 120 + 60})
        eq_(response.status_code, 302)
        eq_(Event.objects.get(id=event.id).duration, 120 + 60)

        # let's unset it
        response = self.client.post(url, {'duration': ''})
        eq_(response.status_code, 302)
        eq_(Event.objects.get(id=event.id).duration, 60 * 5 + 20)
