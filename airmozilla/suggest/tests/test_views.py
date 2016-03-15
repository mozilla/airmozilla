import json
import os
import datetime
import tempfile
import shutil

import pytz
from nose.tools import eq_, ok_

from django.contrib.auth.models import User, Group, Permission
from django.conf import settings
from django.utils import timezone
from django.utils.timezone import utc
from django.core import mail
from django.core.files import File
from django.core.urlresolvers import reverse
from django.utils.encoding import smart_text

from airmozilla.main.models import (
    SuggestedEvent,
    SuggestedEventComment,
    Event,
    Location,
    Channel,
    Tag,
    Picture,
    Topic,
)
from airmozilla.comments.models import SuggestedDiscussion
from airmozilla.base.tests.testbase import DjangoTestCase

_here = os.path.dirname(__file__)
HAS_OPENGRAPH_FILE = os.path.join(_here, 'has_opengraph.html')
PNG_FILE = os.path.join(_here, 'popcorn.png')


class HeadResponse(object):
    def __init__(self, **headers):
        self.headers = headers


class TestPages(DjangoTestCase):
    placeholder = 'airmozilla/manage/tests/firefox.png'

    def setUp(self):
        super(TestPages, self).setUp()
        self.user = User.objects.create_superuser('fake', 'fake@f.com', 'fake')
        assert self.client.login(username='fake', password='fake')
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        super(TestPages, self).tearDown()
        shutil.rmtree(self.tmp_dir)

    def _make_suggested_event(
        self,
        title="Cool O'Title",
        slug='cool-title',
        description='Some long description',
        short_description='Short description',
        additional_links='http://www.peterbe.com\n',
        location=None,
        start_time=None,
    ):
        location = location or Location.objects.get(name='Mountain View')
        start_time = start_time or datetime.datetime(
            2014, 1, 1, 12, 0, 0
        )
        start_time = start_time.replace(tzinfo=utc)

        event = SuggestedEvent.objects.create(
            user=self.user,
            title=title,
            slug=slug,
            description=description,
            short_description=short_description,
            location=location,
            start_time=start_time,
            additional_links=additional_links,
        )
        tag1 = Tag.objects.create(name='Tag1')
        tag2 = Tag.objects.create(name='Tag2')
        event.tags.add(tag1)
        event.tags.add(tag2)
        channel = Channel.objects.create(name='ChannelX', slug='channelx')
        event.channels.add(channel)

        return event

    def test_link_to_suggest(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.placeholder)
        response = self.client.get('/')
        eq_(response.status_code, 200)
        start_url = reverse('suggest:start')
        response_content = response.content.decode('utf-8')
        ok_(start_url in response_content)

    def test_unauthorized(self):
        """ Client with no log in - should be rejected. """
        self.client.logout()
        response = self.client.get(reverse('suggest:start'))
        self.assertRedirects(
            response, settings.LOGIN_URL +
            '?next=' + reverse('suggest:start')
        )

    def test_start(self):
        url = reverse('suggest:start')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        response = self.client.post(url, {
            'title': 'A New World',
        })
        eq_(response.status_code, 302)

        event = SuggestedEvent.objects.get(title='A New World')
        url = reverse('suggest:description', args=(event.pk,))
        eq_(event.slug, 'a-new-world')
        ok_(not event.start_time)
        eq_(event.status, SuggestedEvent.STATUS_CREATED)
        self.assertRedirects(response, url)

    def test_start_duplicate_slug(self):
        event = Event.objects.get(slug='test-event')
        event.title = 'Some Other Title'
        event.save()
        url = reverse('suggest:start')
        response = self.client.post(url, {
            'title': 'TEST Event',
        })
        eq_(response.status_code, 302)
        suggested_event, = SuggestedEvent.objects.all()
        eq_(
            suggested_event.slug,
            'test-event-2'
        )

    def test_start_duplicate_slug_desperate(self):
        today = timezone.now()
        event = Event.objects.get(slug='test-event')
        event.title = 'Some Other Title'
        event.save()

        Event.objects.create(
            title='Entirely Different',
            slug=today.strftime('test-event-%Y%m%d'),
            start_time=today,
        )
        url = reverse('suggest:start')
        response = self.client.post(url, {
            'title': 'TEST Event',
        })
        eq_(response.status_code, 302)
        suggested_event, = SuggestedEvent.objects.all()
        eq_(
            suggested_event.slug,
            'test-event-2'
        )

    def test_start_duplicate_title(self):
        SuggestedEvent.objects.create(
            user=self.user,
            title='A New World',
            slug='a-new-world',
            short_description='Short Description',
            description='Long Description',
        )
        url = reverse('suggest:start')
        response = self.client.post(url, {
            'title': 'A New World',
        })
        eq_(response.status_code, 302)
        eq_(SuggestedEvent.objects.filter(title='A New World').count(), 2)
        eq_(SuggestedEvent.objects.filter(slug='a-new-world').count(), 1)
        eq_(SuggestedEvent.objects.filter(slug='a-new-world-2').count(), 1)

    def test_start_invalid_entry(self):
        # you can either get a form error if the slug is already
        # taken by an event or if only a title is entered and no slug,
        # but the autogenerated slug is taken

        # know thee fixtures
        Event.objects.get(title='Test event', slug='test-event')
        url = reverse('suggest:start')

        response = self.client.post(url, {'title': ''})
        eq_(response.status_code, 200)
        ok_('Form error' in response.content)

        response = self.client.post(url, {'title': 'Cool Title'})
        eq_(response.status_code, 302)
        suggested_event, = SuggestedEvent.objects.all()
        eq_(suggested_event.title, 'Cool Title')
        eq_(suggested_event.slug, 'cool-title')

    def test_title(self):
        event = SuggestedEvent.objects.create(
            user=self.user,
            title='Cool Title',
            slug='cool-title',
        )
        url = reverse('suggest:title', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        data = {
            'title': '',
            'slug': 'contains spaces',
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 200)
        ok_('Form errors' in response.content)

        data = {
            'title': 'New Title',
            'slug': 'new-slug',
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        next_url = reverse('suggest:description', args=(event.pk,))
        self.assertRedirects(response, next_url)

    def test_upload_placeholder(self):
        location, = Location.objects.filter(name='Mountain View')
        today = timezone.now()
        event = SuggestedEvent.objects.create(
            user=self.user,
            title='Cool Title',
            slug='cool-title',
            short_description='Short Description',
            description='Description',
            start_time=today,
            location=location
        )
        url = reverse('suggest:placeholder', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        with open(self.placeholder) as fp:
            data = {'placeholder_img': fp}
            response = self.client.post(url, data)
        eq_(response.status_code, 302)
        next_url = reverse('suggest:summary', args=(event.pk,))
        self.assertRedirects(response, next_url)

    def test_select_placeholder_from_gallery(self):
        location, = Location.objects.filter(name='Mountain View')
        today = timezone.now()
        event = SuggestedEvent.objects.create(
            user=self.user,
            title='Cool Title',
            slug='cool-title',
            short_description='Short Description',
            description='Description',
            start_time=today,
            location=location
        )
        url = reverse('suggest:placeholder', args=(event.pk,))
        with open(self.placeholder) as fp:
            picture_id = Picture.objects.create(file=File(fp)).id
        response = self.client.get(url)
        eq_(response.status_code, 200)

        data = {'picture': picture_id}
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        next_url = reverse('suggest:summary', args=(event.pk,))
        self.assertRedirects(response, next_url)

    def test_change_picture(self):
        location, = Location.objects.filter(name='Mountain View')
        today = timezone.now()
        with open(self.placeholder) as fp:
            picture = Picture.objects.create(file=File(fp))
        event = SuggestedEvent.objects.create(
            user=self.user,
            title='Cool Title',
            slug='cool-title',
            short_description='Short Description',
            description='Description',
            start_time=today,
            location=location,
            picture=picture
        )
        url = reverse('suggest:placeholder', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        data = {'picture': picture.id}
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        next_url = reverse('suggest:summary', args=(event.pk,))
        self.assertRedirects(response, next_url)

    def test_creating_event_without_placeholder_or_picture(self):
        location, = Location.objects.filter(name='Mountain View')
        today = timezone.now()
        event = SuggestedEvent.objects.create(
            user=self.user,
            title='Cool Title',
            slug='cool-title',
            short_description='Short Description',
            description='Description',
            start_time=today,
            location=location
        )
        url = reverse('suggest:placeholder', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        data = {}
        response = self.client.post(url, data)
        ok_('Events needs to have a picture' in
            response.context['form'].errors['__all__'])

    def test_not_yours_to_edit(self):
        jane = User.objects.create_user('jane')
        event = SuggestedEvent.objects.create(
            user=jane,
            title='Cool Title',
            slug='cool-title',
        )
        url = reverse('suggest:title', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 400)

        url = reverse('suggest:description', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 400)

        url = reverse('suggest:details', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 400)

        url = reverse('suggest:placeholder', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 400)

        url = reverse('suggest:summary', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 400)

        # and not yours to delete
        url = reverse('suggest:delete', args=(event.pk,))
        response = self.client.post(url)
        eq_(response.status_code, 400)

    def test_description(self):
        event = SuggestedEvent.objects.create(
            user=self.user,
            title='Cool Title',
            slug='cool-title',
        )
        url = reverse('suggest:description', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        data = {
            'description': 'This is my cool description ',
            'short_description': ' '
        }

        response = self.client.post(url, data)
        next_url = reverse('suggest:details', args=(event.pk,))
        self.assertRedirects(response, next_url)
        event = SuggestedEvent.objects.get(pk=event.pk)
        eq_(event.description, data['description'].strip())
        eq_(event.short_description, data['short_description'].strip())

        data['short_description'] = 'Really cool '
        response = self.client.post(url, data)
        self.assertRedirects(response, next_url)
        event = SuggestedEvent.objects.get(pk=event.pk)
        eq_(event.description, data['description'].strip())
        eq_(event.short_description, data['short_description'].strip())

        # XXX should there be some length restrictions
        # on `description` or `short_description`?

    def test_details(self):
        event = SuggestedEvent.objects.create(
            user=self.user,
            title='Cool Title',
            slug='cool-title',
            description='Some long description',
            short_description=''
        )
        url = reverse('suggest:details', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        mv = Location.objects.get(name='Mountain View')
        channel = Channel.objects.create(
            name='Security',
            slug='security'
        )
        tag1 = Tag.objects.create(
            name='foo'
        )
        tag2 = Tag.objects.create(
            name='bar'
        )

        data = {
            'start_time': '2021-01-01 12:00:00',
            'estimated_duration': str(60 * 60 * 2),
            'timezone': 'US/Pacific',
            'location': mv.pk,
            'privacy': Event.PRIVACY_CONTRIBUTORS,
            'tags': [tag1.name, tag2.name],
            'channels': channel.pk,
            'additional_links': 'http://www.peterbe.com\n',
            'call_info': 'vidyo room',
        }

        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        next_url = reverse('suggest:placeholder', args=(event.pk,))
        self.assertRedirects(response, next_url)

        event = SuggestedEvent.objects.get(pk=event.pk)

        # 1st January 2021 at 12:00 in US/Pacific is 20:00 in UTC
        eq_(event.start_time.strftime('%Y-%m-%d'), '2021-01-01')
        eq_(event.start_time.strftime('%H:%M'), '20:00')
        eq_(event.start_time.tzname(), 'UTC')
        eq_(event.estimated_duration, 60 * 60 * 2)
        eq_(event.location, mv)
        eq_([x.name for x in event.tags.all()], ['foo', 'bar'])
        eq_(event.channels.all()[0], channel)
        eq_(event.additional_links, data['additional_links'].strip())
        eq_(event.call_info, 'vidyo room')

        # do it again, but now with different tags
        data['tags'] = ['buzz', 'bar']
        response = self.client.post(url, data)
        eq_(response.status_code, 302)

        event = SuggestedEvent.objects.get(pk=event.pk)
        eq_(
            sorted(x.name for x in event.tags.all()),
            sorted(['bar', 'buzz'])
        )

    def test_details_discussion_stays_disabled(self):
        event = SuggestedEvent.objects.create(
            user=self.user,
            title='No discussion please!',
            slug='no-discussion',
            description='I don\'t like critisism',
            short_description=''
        )
        url = reverse('suggest:details', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response.context['form']['enable_discussion'].value(), False)

    def test_details_enable_discussion(self):
        assert self.client.login(username='fake', password='fake')
        event = SuggestedEvent.objects.create(
            user=self.user,
            title='Cool Title',
            slug='cool-title',
            description='Some long description',
            short_description=''
        )
        url = reverse('suggest:details', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        mv = Location.objects.get(name='Mountain View')
        channel = Channel.objects.create(
            name='Security',
            slug='security'
        )

        data = {
            'start_time': '2021-01-01 12:00:00',
            'estimated_duration': '3600',
            'timezone': 'US/Pacific',
            'location': mv.pk,
            'privacy': Event.PRIVACY_CONTRIBUTORS,
            'channels': channel.pk,
            'enable_discussion': True
        }

        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        next_url = reverse('suggest:discussion', args=(event.pk,))
        self.assertRedirects(response, next_url)
        discussion = SuggestedDiscussion.objects.get(
            event=event,
            enabled=True
        )
        eq_(discussion.moderators.all().count(), 1)
        ok_(self.user in discussion.moderators.all())

        # assert that we're still signed in
        assert self.client.session['_auth_user_id']

        # do it a second time and it shouldn't add us as a moderator again
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        self.assertRedirects(response, next_url)
        discussion = SuggestedDiscussion.objects.get(pk=discussion.pk)
        eq_(discussion.moderators.all().count(), 1)

        # this time, disable it
        response = self.client.post(url, dict(data, enable_discussion=False))
        eq_(response.status_code, 302)
        next_url = reverse('suggest:placeholder', args=(event.pk,))
        self.assertRedirects(response, next_url)
        discussion = SuggestedDiscussion.objects.get(pk=discussion.pk)
        ok_(not discussion.enabled)

    def test_details_disbled_location_options(self):
        mv = Location.objects.get(name='Mountain View')
        # create two other locations
        Location.objects.create(
            name='Atlantis',
            timezone='US/Pacific',
            is_active=False
        )
        babylon = Location.objects.create(
            name='Babylon',
            timezone='US/Pacific'
        )
        event = SuggestedEvent.objects.create(
            user=self.user,
            title='Cool Title',
            slug='cool-title',
            description='Some long description',
            short_description=''
        )
        url = reverse('suggest:details', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        ok_('Atlantis' not in response.content)
        ok_('Babylon' in response.content)
        # one of the fixtures
        ok_('Mountain View' in response.content)

        channel = Channel.objects.create(
            name='Security',
            slug='security'
        )

        data = {
            'start_time': '2021-01-01 12:00:00',
            'estimated_duration': '3600',
            'timezone': 'US/Pacific',
            'location': babylon.pk,
            'privacy': Event.PRIVACY_CONTRIBUTORS,
            'channels': channel.pk,
            'enable_discussion': True
        }

        response = self.client.post(url, data)
        eq_(response.status_code, 302)

        # Now suppose Babylon becomes inactive too
        babylon.is_active = False
        babylon.save()

        # go back to edit again
        response = self.client.get(url)
        eq_(response.status_code, 200)

        ok_('Atlantis' not in response.content)
        # available because it was chosen
        ok_('Babylon' in response.content)
        ok_('Mountain View' in response.content)

        # but suppose we now switch to Mountain View
        data['location'] = mv.pk
        response = self.client.post(url, data)
        eq_(response.status_code, 302)

        # now we can't go back to Babylon again
        response = self.client.get(url)
        eq_(response.status_code, 200)

        ok_('Atlantis' not in response.content)
        ok_('Babylon' not in response.content)
        ok_('Mountain View' in response.content)

    def test_details_timezone_formatting(self):
        location = Location.objects.create(
            name='Paris',
            timezone='Europe/Paris'
        )
        start_time = datetime.datetime(
            2013, 5, 6, 11, 0, 0
        ).replace(tzinfo=utc)
        event = SuggestedEvent.objects.create(
            user=self.user,
            title='Cool Title',
            slug='cool-title',
            description='Some long description',
            short_description='',
            location=location,
            privacy=Event.PRIVACY_PUBLIC,
            start_time=start_time,
        )
        url = reverse('suggest:details', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # the location is `US/Pacific` which means at 13:00 UTC,
        # the time is expected to be 05:00 in US/Pacific
        as_string = '2013-05-06 13:00:00'
        ok_('value="%s"' % as_string in response.content)

    def test_details_default_channel(self):
        event = SuggestedEvent.objects.create(
            user=self.user,
            title='Cool Title',
            slug='cool-title',
            description='Some long description',
            short_description=''
        )
        url = reverse('suggest:details', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        mv = Location.objects.get(name='Mountain View')
        future = (
            datetime.datetime(2021, 1, 1, 10, 0)
        )
        tz = pytz.timezone('US/Pacific')
        future = future.replace(tzinfo=tz)
        data = {
            'start_time': future.strftime('%Y-%m-%d %H:%M'),
            'estimated_duration': '3600',
            'timezone': 'US/Pacific',
            'location': mv.pk,
            'privacy': Event.PRIVACY_CONTRIBUTORS,
            'tags': '',
        }
        assert 'channel' not in data
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        event = SuggestedEvent.objects.get(pk=event.pk)
        eq_(event.channels.all().count(), 1)
        eq_(
            [x.pk for x in event.channels.all()],
            [x.pk for x in
             Channel.objects.filter(slug=settings.DEFAULT_CHANNEL_SLUG)]
        )

    def test_discussion(self):
        location, = Location.objects.filter(name='Mountain View')
        today = timezone.now()
        event = SuggestedEvent.objects.create(
            user=self.user,
            title='Cool Title',
            slug='cool-title',
            short_description='Short Description',
            description='Description',
            start_time=today,
            location=location
        )
        discussion = SuggestedDiscussion.objects.create(
            event=event,
            enabled=True,
            notify_all=True,
            moderate_all=True,
        )
        discussion.moderators.add(self.user)
        url = reverse('suggest:discussion', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        data = {
            'enabled': True,
            'moderate_all': True,
            'emails': [self.user.email],
        }
        # disable it
        response = self.client.post(url, dict(data, enabled=False))
        eq_(response.status_code, 302)
        next_url = reverse('suggest:placeholder', args=(event.pk,))
        self.assertRedirects(response, next_url)
        discussion = SuggestedDiscussion.objects.get(pk=discussion.pk)
        ok_(not discussion.enabled)
        # reset that
        discussion.enabled = True

        # try to add something that doesn't look like a valid email address
        response = self.client.post(url, dict(data, emails=['not an email']))
        eq_(response.status_code, 200)

        # add two new emails one of which we don't already have a user for
        bob = User.objects.create_user('bob', 'bob@mozilla.com', 'secret')
        # note the deliberate duplicate only different in case
        emails = [
            self.user.email,
            bob.email,
            self.user.email.upper(),
        ]
        response = self.client.post(url, dict(data, emails=emails))
        eq_(response.status_code, 302)
        self.assertRedirects(response, next_url)
        eq_(discussion.moderators.all().count(), 2)

        # if you now open the form again these emails should be in there
        # already
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # it can't trust the sort order on these expected email addresses
        ok_('fake@f.com' in response.content)
        ok_('bob@mozilla.com' in response.content)

    def test_discussion_default_moderator(self):
        location, = Location.objects.filter(name='Mountain View')
        today = timezone.now()
        event = SuggestedEvent.objects.create(
            user=self.user,
            title='Cool Title',
            slug='cool-title',
            short_description='Short Description',
            description='Description',
            start_time=today,
            location=location
        )
        discussion = SuggestedDiscussion.objects.create(
            event=event,
            enabled=True,
            notify_all=True,
            moderate_all=True,
        )
        discussion.moderators.add(self.user)
        url = reverse('suggest:discussion', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(self.user.email in smart_text(response.content))

        # suppose you have previously saved that there should another
        # moderator that isn't you
        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        discussion.moderators.clear()
        discussion.moderators.add(bob)
        response = self.client.get(url)
        eq_(response.status_code, 200)
        content = smart_text(response.content)
        ok_(bob.email in content)
        ok_(self.user.email not in content)

    def test_autocomplete_email(self):
        url = reverse('suggest:autocomplete_emails')

        response = self.client.get(url)
        eq_(response.status_code, 400)
        response = self.client.get(url, {'q': ''})
        eq_(response.status_code, 200)
        emails = json.loads(response.content)['emails']
        eq_(emails, [])

        # fake@f.com is the user set up in the fixtures
        response = self.client.get(url, {'q': 'fake'})
        emails = json.loads(response.content)['emails']
        eq_(emails, ['fake@f.com'])

        # searching for something that isn't an email address
        # should suggest <q>@mozilla.com
        response = self.client.get(url, {'q': 'start'})
        emails = json.loads(response.content)['emails']
        eq_(emails, ['start@mozilla.com'])

        # searching for something that doesn't exist and isn't a valid
        # email, nothing should be found
        response = self.client.get(url, {'q': 'afweef@asd'})
        emails = json.loads(response.content)['emails']
        eq_(emails, [])

        # searching for a valid email address should return it
        response = self.client.get(url, {'q': 'mail@peterbe.com'})
        emails = json.loads(response.content)['emails']
        eq_(emails, ['mail@peterbe.com'])

    def test_summary(self):
        event = self._make_suggested_event()
        url = reverse('suggest:summary', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        ok_('Location' in response.content)
        ok_('Start time' in response.content)
        ok_('Remote presenters' in response.content)
        ok_('Vidyo room' in response.content)

        ok_("Cool O&#39;Title" in response.content)
        ok_('cool-title' in response.content)
        ok_('Some long description' in response.content)
        ok_('Short description' in response.content)
        ok_('Mountain View' in response.content)
        ok_('US/Pacific' in response.content)
        ok_('12:00' in response.content)
        ok_('Tag1' in response.content)
        ok_('Tag2' in response.content)
        ok_('ChannelX' in response.content)
        ok_(
            '<a href="http://www.peterbe.com">http://www.peterbe.com</a>'
            in response.content
        )
        # there should also be links to edit things
        response_content = response.content.decode('utf-8')
        ok_(reverse('suggest:title', args=(event.pk,)) in response_content)
        ok_(reverse('suggest:description', args=(event.pk,))
            in response_content)
        ok_(reverse('suggest:details', args=(event.pk,)) in response_content)
        ok_(reverse('suggest:placeholder', args=(event.pk,))
            in response_content)
        # the event is not submitted yet
        ok_('Submit for review' in response_content)

    def test_summary_with_discussion(self):
        event = self._make_suggested_event()
        url = reverse('suggest:summary', args=(event.pk,))

        discussion = SuggestedDiscussion.objects.create(
            enabled=True,
            moderate_all=True,
            notify_all=True,
            event=event
        )
        bob = User.objects.create(email='bob@mozilla.com')
        discussion.moderators.add(self.user)
        discussion.moderators.add(bob)

        response = self.client.get(url)
        eq_(response.status_code, 200)
        content = smart_text(response.content)
        ok_('Enabled' in content)
        ok_(self.user.email in content)
        ok_(bob.email in content)

        # and there should be a link to change the discussion
        discussion_url = reverse('suggest:discussion', args=(event.pk,))
        response_content = response.content.decode('utf-8')
        ok_(discussion_url in response_content)

        discussion.enabled = False
        discussion.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Enabled' not in response.content)
        ok_('Not enabled' in response.content)

    def test_summary_after_event_approved(self):
        event = self._make_suggested_event()
        now = timezone.now()
        event.first_submitted = now
        event.submitted = now
        url = reverse('suggest:summary', args=(event.pk,))
        real = Event.objects.create(
            title=event.title,
            slug=event.slug,
            description=event.description,
            start_time=event.start_time,
            location=event.location,
            placeholder_img=event.placeholder_img,
            privacy=event.privacy,
        )
        event.accepted = real
        event.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Accepted!' in response.content)
        ok_('Submit for review' not in response.content)
        real_url = reverse('main:event', args=(real.slug,))
        response_content = response.content.decode('utf-8')
        ok_(real_url not in response_content)

        # now schedule the real event
        real.status = Event.STATUS_SCHEDULED
        real.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Accepted!' in response.content)
        ok_('accepted and scheduled' in response.content)
        ok_('Submit for review' not in response.content)
        response_content = response.content.decode('utf-8')
        ok_(real_url in response_content)

        # suppose we change the start time
        real.start_time += datetime.timedelta(hours=1)
        real.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(
            'The <b>scheduled time</b> is different from what you requested'
            in response.content
        )

        toronto = Location.objects.create(
            name='Toronto',
            timezone='Canada/Eastern'
        )
        real.location = toronto
        real.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(
            'The <b>scheduled location</b> is different from what '
            'you requested'
            in response.content
        )

    def test_delete(self):
        event = SuggestedEvent.objects.create(
            user=self.user,
            title='Cool Title',
            slug='cool-title',
            description='Some long description',
            short_description=''
        )

        url = reverse('suggest:delete', args=(event.pk,))
        response = self.client.post(url)
        eq_(response.status_code, 302)
        next_url = reverse('suggest:start')
        self.assertRedirects(response, next_url)
        ok_(not SuggestedEvent.objects.all().count())

    def test_view_someone_elses_suggested_summary(self):
        event = self._make_suggested_event()
        event.user = User.objects.create_user('lonnen')
        event.save()
        url = reverse('suggest:summary', args=(event.pk,))

        richard = User.objects.create_user('richard', password='secret')
        # but it should be ok if self.user had the add_event permission
        assert self.client.login(username='richard', password='secret')

        response = self.client.get(url)
        eq_(response.status_code, 400)
        # give Richard the add_event permission
        permission = Permission.objects.get(codename='add_event')
        richard.user_permissions.add(permission)

        response = self.client.get(url)
        eq_(response.status_code, 400)
        # because it's not submitted
        event.submitted = timezone.now()
        event.save()

        # finally
        response = self.client.get(url)
        eq_(response.status_code, 200)

    def test_submit_event(self):
        event = self._make_suggested_event()
        ok_(not event.submitted)
        eq_(event.status, SuggestedEvent.STATUS_CREATED)
        url = reverse('suggest:summary', args=(event.pk,))
        assert self.client.get(url).status_code == 200

        # before we submit it, we need to create some users
        # who should get the email notification
        group, _ = Group.objects.get_or_create(
            name=settings.NOTIFICATIONS_GROUP_NAME
        )
        richard = User.objects.create_user(
            'richard',
            email='richard@mozilla.com'
        )
        richard.groups.add(group)

        response = self.client.post(url)
        eq_(response.status_code, 302)

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Submitted' in response.content)
        event = SuggestedEvent.objects.get(pk=event.pk)
        ok_(event.submitted)
        eq_(event.status, SuggestedEvent.STATUS_SUBMITTED)

        # that should have sent out some emails
        email_sent = mail.outbox[-1]
        ok_(event.title in email_sent.subject)
        eq_(email_sent.from_email, settings.EMAIL_FROM_ADDRESS)
        ok_('richard@mozilla.com' in email_sent.recipients())
        ok_('US/Pacific' in email_sent.body)
        ok_(event.user.email in email_sent.body)
        ok_(event.title in email_sent.body)
        ok_(event.location.name in email_sent.body)
        # The event starts at 12 UTC (see _make_suggested_event())
        # In US/Pacific that's 04:00
        ok_('04:00' in email_sent.body)
        summary_url = reverse('suggest:summary', args=(event.pk,))
        ok_(summary_url in email_sent.body)
        manage_url = reverse('manage:suggestions')
        ok_(manage_url in email_sent.body)

        # if you do it a second time, it'll un-submit
        response = self.client.post(url)
        eq_(response.status_code, 302)
        event = SuggestedEvent.objects.get(pk=event.pk)
        ok_(not event.submitted)
        eq_(event.status, SuggestedEvent.STATUS_RETRACTED)

    def test_submit_event_with_topics(self):
        event = self._make_suggested_event()
        topic = Topic.objects.create(
            topic='Money Matters',
            is_active=True
        )
        group = Group.objects.create(name='PR')
        richard = User.objects.create_user(
            'richard',
            email='richard@mozilla.com'
        )
        richard.groups.add(group)
        topic.groups.add(group)
        event.topics.add(topic)
        url = reverse('suggest:summary', args=(event.pk,))
        response = self.client.post(url)
        eq_(response.status_code, 302)
        event = SuggestedEvent.objects.get(pk=event.pk)
        ok_(event.topics.all())

    def test_title_edit(self):
        event = SuggestedEvent.objects.create(
            user=self.user,
            title='Cool Title',
            slug='cool-title',
        )
        url = reverse('suggest:title', args=(event.pk,))

        real_event, = Event.objects.all()
        data = {
            'title': real_event.title.upper(),
            'slug': ''
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 200)
        ok_('Form errors' in response.content)

        data = {
            'title': 'Something entirely different',
            'slug': real_event.slug.upper()
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 200)
        ok_('Form errors' in response.content)

        data = {
            'title': 'Something entirely different',
            'slug': ''
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        event = SuggestedEvent.objects.get(pk=event.pk)
        eq_(event.slug, 'something-entirely-different')

        # try with something unicodish
        data = {
            'title': u'Walking down the stra\xdfe',
            'slug': ''
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        event = SuggestedEvent.objects.get(pk=event.pk)
        eq_(event.slug, 'walking-down-the-strasse')

    def test_add_comments_in_summary_before_submission(self):
        # also need a superuser
        User.objects.create(
            username='zandr',
            email='zandr@mozilla.com',
            is_staff=True,
            is_superuser=True
        )

        event = self._make_suggested_event()
        # give it an exceptionally long title
        event.title = 'Title' * 10
        event.save()
        ok_(not event.submitted)
        url = reverse('suggest:summary', args=(event.pk,))
        assert self.client.get(url).status_code == 200

        # before anything, we need to create some users
        # who should get the email notification
        group, _ = Group.objects.get_or_create(
            name=settings.NOTIFICATIONS_GROUP_NAME
        )
        richard = User.objects.create_user(
            'richard',
            email='richard@mozilla.com'
        )
        richard.groups.add(group)
        mrinactive = User.objects.create_user(
            'mrinactive',
            email='mr@inactive.com',
        )
        mrinactive.is_active = False
        mrinactive.save()
        mrinactive.groups.add(group)

        data = {
            'save_comment': 1,
            'comment': '',  # not going to be valid
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 200)
        ok_('This field is required' in response.content)

        # this should not have submitted the event
        event = SuggestedEvent.objects.get(pk=event.pk)
        ok_(not event.submitted)

        no_sent_emails = len(mail.outbox)
        ok_(not no_sent_emails)

        # enter a proper comment this time
        data['comment'] = """
        I will need a rubber "duck"
        """
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        # should still not be submitted
        event = SuggestedEvent.objects.get(pk=event.pk)
        ok_(not event.submitted)
        # and no email because it's not submitted yet
        no_sent_emails = len(mail.outbox)
        ok_(not no_sent_emails)
        assert SuggestedEventComment.objects.all().count() == 1

        # submit a second comment
        data['comment'] = "Second comment"
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        assert SuggestedEventComment.objects.all().count() == 2

        # Now, let's submit it
        response = self.client.post(url, {})
        event = SuggestedEvent.objects.get(pk=event.pk)
        ok_(event.submitted)

        email_sent = mail.outbox[-1]
        ok_('richard@mozilla.com' in email_sent.recipients())
        ok_('mr@inactive.com' not in email_sent.recipients())

        ok_('TitleTitle' in email_sent.subject)
        # but it's truncated
        ok_('...' in email_sent.subject)
        ok_(event.title not in email_sent.subject)

        # the two comments should be included in the email
        comment1, comment2 = (
            SuggestedEventComment.objects.all().order_by('created')
        )
        ok_(comment1.comment in email_sent.body)
        ok_(comment2.comment in email_sent.body)

    def test_add_comments_in_summary_after_submission(self):
        # also need a superuser
        User.objects.create(
            username='zandr',
            email='zandr@mozilla.com',
            is_staff=True,
            is_superuser=True
        )
        event = self._make_suggested_event()
        # give it an exceptionally long title
        event.title = 'Title' * 10
        event.submitted = timezone.now()
        event.save()
        url = reverse('suggest:summary', args=(event.pk,))
        assert self.client.get(url).status_code == 200

        # before anything, we need to create some users
        # who should get the email notification
        group, _ = Group.objects.get_or_create(
            name=settings.NOTIFICATIONS_GROUP_NAME
        )
        richard = User.objects.create_user(
            'richard',
            email='richard@mozilla.com'
        )
        richard.groups.add(group)

        data = {
            'save_comment': 1,
            'comment': '',  # not going to be valid
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 200)
        ok_('This field is required' in response.content)

        no_sent_emails = len(mail.outbox)
        ok_(not no_sent_emails)

        # enter a proper comment this time
        data['comment'] = """
        I will need a rubber "duck"
        """
        response = self.client.post(url, data)
        eq_(response.status_code, 302)

        email_sent = mail.outbox[-1]
        ok_('New comment' in email_sent.subject)
        ok_('TitleTitle' in email_sent.subject)
        # but it's truncated
        ok_('...' in email_sent.subject)
        ok_(event.title not in email_sent.subject)
        ok_(data['comment'].strip() in email_sent.body)

    def test_add_comments_in_summary_after_scheduled(self):
        # also need a superuser
        User.objects.create(
            username='zandr',
            email='zandr@mozilla.com',
            is_staff=True,
            is_superuser=True
        )
        event = self._make_suggested_event()
        event.title = 'Title Title Title'
        now = timezone.now()
        event.first_submitted = now
        event.submitted = now
        event.save()

        real = Event.objects.create(
            title=event.title,
            slug=event.slug,
            description=event.description,
            start_time=event.start_time,
            location=event.location,
            placeholder_img=event.placeholder_img,
            privacy=event.privacy,
            status=Event.STATUS_SCHEDULED
        )
        event.accepted = real
        event.save()

        # before anything, we need to create some users
        # who should get the email notification
        group, _ = Group.objects.get_or_create(
            name=settings.NOTIFICATIONS_GROUP_NAME
        )
        richard = User.objects.create_user(
            'richard',
            email='richard@mozilla.com'
        )
        richard.groups.add(group)

        data = {
            'save_comment': 1,
            'comment': 'I will need a white "rabbit"',
        }
        url = reverse('suggest:summary', args=(event.pk,))
        response = self.client.post(url, data)
        eq_(response.status_code, 302)

        email_sent = mail.outbox[-1]
        ok_(data['comment'].strip() in email_sent.body)
        ok_(self.user.email in email_sent.body)

        ok_(url in email_sent.body)
        real_url = reverse('manage:event_edit', args=(real.pk,))
        ok_(real_url in email_sent.body)
