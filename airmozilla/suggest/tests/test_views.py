import datetime
import pytz

from django.test import TestCase
from django.contrib.auth.models import User, Group, Permission
from django.conf import settings
from django.utils.timezone import utc
from django.core import mail

from funfactory.urlresolvers import reverse
from nose.tools import eq_, ok_

from airmozilla.main.models import (
    SuggestedEvent,
    SuggestedEventComment,
    Event,
    Location,
    Channel,
    Category,
    Tag
)


class TestPages(TestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']
    placeholder = 'airmozilla/manage/tests/firefox.png'

    def setUp(self):
        self.user = User.objects.create_superuser('fake', 'fake@f.com', 'fake')
        assert self.client.login(username='fake', password='fake')

    def _make_suggested_event(self,
                              title="Cool O'Title",
                              slug='cool-title',
                              description='Some long description',
                              short_description='Short description',
                              additional_links='http://www.peterbe.com\n',
                              location=None,
                              start_time=None,
                              category=None,
                              ):
        location = location or Location.objects.get(name='Mountain View')
        start_time = start_time or datetime.datetime(
            2014, 1, 1, 12, 0, 0
        )
        start_time = start_time.replace(tzinfo=utc)
        category = category or Category.objects.create(name='CategoryX')

        event = SuggestedEvent.objects.create(
            user=self.user,
            title=title,
            slug=slug,
            description=description,
            short_description=short_description,
            location=location,
            start_time=start_time,
            additional_links=additional_links,
            category=category,
        )
        tag1 = Tag.objects.create(name='Tag1')
        tag2 = Tag.objects.create(name='Tag2')
        event.tags.add(tag1)
        event.tags.add(tag2)
        channel = Channel.objects.create(name='ChannelX', slug='channelx')
        event.channels.add(channel)

        return event

    def test_link_to_suggest(self):
        start_url = reverse('suggest:start')
        response = self.client.get('/')
        eq_(response.status_code, 200)
        ok_(start_url in response.content)

    def test_unauthorized(self):
        """ Client with no log in - should be rejected. """
        self.client.logout()
        response = self.client.get(reverse('suggest:start'))
        self.assertRedirects(response, settings.LOGIN_URL
                             + '?next=' + reverse('suggest:start'))

    def test_start(self):
        url = reverse('suggest:start')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        response = self.client.post(url, {'title': 'A New World'})
        eq_(response.status_code, 302)

        event = SuggestedEvent.objects.get(title='A New World')
        url = reverse('suggest:description', args=(event.pk,))
        eq_(event.slug, 'a-new-world')
        self.assertRedirects(response, url)

    def test_start_duplicate_slug(self):
        event = Event.objects.get(slug='test-event')
        event.title = 'Some Other Title'
        event.save()
        url = reverse('suggest:start')
        response = self.client.post(url, {'title': 'TEST Event'})
        eq_(response.status_code, 302)
        suggested_event, = SuggestedEvent.objects.all()
        today = datetime.datetime.utcnow()
        eq_(
            suggested_event.slug,
            today.strftime('test-event-%Y%m%d')
        )

    def test_start_duplicate_slug_desperate(self):
        today = datetime.datetime.utcnow()
        event = Event.objects.get(slug='test-event')
        event.title = 'Some Other Title'
        event.save()

        Event.objects.create(
            title='Entirely Different',
            slug=today.strftime('test-event-%Y%m%d'),
            start_time=today.replace(tzinfo=utc),
        )
        url = reverse('suggest:start')
        response = self.client.post(url, {'title': 'TEST Event'})
        eq_(response.status_code, 302)
        suggested_event, = SuggestedEvent.objects.all()
        eq_(
            suggested_event.slug,
            today.strftime('test-event-%Y%m%d-2')
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
        response = self.client.post(url, {'title': 'A New World'})
        eq_(response.status_code, 200)
        ok_(
            'You already have a suggest event with this title'
            in response.content
        )

    def test_start_invalid_entry(self):
        # you can either get a form error if the slug is already
        # taken by an event or if only a title is entered and no slug,
        # but the autogenerated slug is taken

        # know thee fixtures
        Event.objects.get(title='Test event', slug='test-event')
        url = reverse('suggest:start')

        response = self.client.post(url, {'title': 'TEST Event'})
        eq_(response.status_code, 200)
        ok_('Form error' in response.content)

        response = self.client.post(
            url,
            {'title': 'Cool Title'}
        )
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
            'slug': 'contains spaces'
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
        today = datetime.datetime.utcnow()
        event = SuggestedEvent.objects.create(
            user=self.user,
            title='Cool Title',
            slug='cool-title',
            short_description='Short Description',
            description='Description',
            start_time=today.replace(tzinfo=utc),
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
        category = Category.objects.get(name='testing')
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
            'timezone': 'US/Pacific',
            'location': mv.pk,
            'privacy': Event.PRIVACY_CONTRIBUTORS,
            'category': category.pk,
            'tags': tag1.name + ', ' + tag2.name,
            'channels': channel.pk,
            'additional_links': 'http://www.peterbe.com\n',
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
        eq_(event.location, mv)
        eq_(event.category, category)
        eq_([x.name for x in event.tags.all()], ['foo', 'bar'])
        eq_(event.channels.all()[0], channel)
        eq_(event.additional_links, data['additional_links'].strip())

        # do it again, but now with different tags
        data['tags'] = 'buzz, bar'
        response = self.client.post(url, data)
        eq_(response.status_code, 302)

        event = SuggestedEvent.objects.get(pk=event.pk)
        eq_(
            sorted(x.name for x in event.tags.all()),
            sorted(['bar', 'buzz'])
        )

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
            'timezone': 'US/Pacific',
            'location': mv.pk,
            'privacy': Event.PRIVACY_CONTRIBUTORS,
            'category': '',
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

    def test_summary(self):
        event = self._make_suggested_event()
        url = reverse('suggest:summary', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_("Cool O&#39;Title" in response.content)
        ok_('cool-title' in response.content)
        ok_('Some long description' in response.content)
        ok_('Short description' in response.content)
        ok_('Mountain View' in response.content)
        ok_('US/Pacific' in response.content)
        ok_('12:00' in response.content)
        ok_('Tag1' in response.content)
        ok_('Tag2' in response.content)
        ok_('CategoryX' in response.content)
        ok_('ChannelX' in response.content)
        ok_(
            '<a href="http://www.peterbe.com">http://www.peterbe.com</a>'
            in response.content
        )
        # there should also be links to edit things
        ok_(reverse('suggest:title', args=(event.pk,)) in response.content)
        ok_(reverse('suggest:description', args=(event.pk,))
            in response.content)
        ok_(reverse('suggest:details', args=(event.pk,)) in response.content)
        ok_(reverse('suggest:placeholder', args=(event.pk,))
            in response.content)
        # the event is not submitted yet
        ok_('Submit for review' in response.content)

    def test_summary_after_event_approved(self):
        event = self._make_suggested_event()
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
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
            category=event.category,
        )
        event.accepted = real
        event.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Accepted!' in response.content)
        ok_('Submit for review' not in response.content)
        real_url = reverse('main:event', args=(real.slug,))
        ok_(real_url not in response.content)

        # now schedule the real event
        real.status = Event.STATUS_SCHEDULED
        real.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Accepted!' in response.content)
        ok_('accepted and scheduled' in response.content)
        ok_('Submit for review' not in response.content)
        ok_(real_url in response.content)

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
        event.submitted = datetime.datetime.utcnow().replace(tzinfo=utc)
        event.save()

        # finally
        response = self.client.get(url)
        eq_(response.status_code, 200)

    def test_submit_event(self):
        # create a superuser who will automatically get all notifications
        User.objects.create(
            username='zandr',
            email='zandr@mozilla.com',
            is_staff=True,
            is_superuser=True
        )

        event = self._make_suggested_event()
        ok_(not event.submitted)
        url = reverse('suggest:summary', args=(event.pk,))
        assert self.client.get(url).status_code == 200

        # before we submit it, we need to create some users
        # who should get the email notification
        approvers = Group.objects.get(name='testapprover')
        richard = User.objects.create_user(
            'richard',
            email='richard@mozilla.com'
        )
        richard.groups.add(approvers)
        permission = Permission.objects.get(codename='add_event')
        approvers.permissions.add(permission)

        response = self.client.post(url)
        eq_(response.status_code, 302)

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Submitted' in response.content)
        event = SuggestedEvent.objects.get(pk=event.pk)
        ok_(event.submitted)

        # that should have sent out some emails
        email_sent = mail.outbox[-1]
        ok_(event.title in email_sent.subject)
        eq_(email_sent.from_email, settings.EMAIL_FROM_ADDRESS)
        ok_('richard@mozilla.com' in email_sent.recipients())
        ok_('zandr@mozilla.com' in email_sent.recipients())
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
        approvers = Group.objects.get(name='testapprover')
        richard = User.objects.create_user(
            'richard',
            email='richard@mozilla.com'
        )
        richard.groups.add(approvers)
        mrinactive = User.objects.create_user(
            'mrinactive',
            email='mr@inactive.com',
        )
        mrinactive.is_active = False
        mrinactive.save()
        mrinactive.groups.add(approvers)
        permission = Permission.objects.get(codename='add_event')
        approvers.permissions.add(permission)

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

        ok_('zandr@mozilla.com' in email_sent.recipients())
        ok_('richard@mozilla.com' in email_sent.recipients())
        ok_(self.user.email in email_sent.recipients())
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
        event.submitted = datetime.datetime.utcnow().replace(tzinfo=utc)
        event.save()
        url = reverse('suggest:summary', args=(event.pk,))
        assert self.client.get(url).status_code == 200

        # before anything, we need to create some users
        # who should get the email notification
        approvers = Group.objects.get(name='testapprover')
        richard = User.objects.create_user(
            'richard',
            email='richard@mozilla.com'
        )
        richard.groups.add(approvers)
        permission = Permission.objects.get(codename='add_event')
        approvers.permissions.add(permission)

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
