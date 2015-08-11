import datetime
import os

from nose.tools import eq_, ok_

from django.contrib.auth.models import User, Group, Permission
from django.utils import timezone
from django.core import mail

from funfactory.urlresolvers import reverse

from airmozilla.main.models import (
    Event,
    Channel,
    Tag,
    SuggestedEvent,
    Location,
    SuggestedEventComment,
    Template,
    LocationDefaultEnvironment,
    Approval,
    Topic,
)
from airmozilla.comments.models import (
    Discussion,
    SuggestedDiscussion
)
from .base import ManageTestCase


class TestSuggestions(ManageTestCase):

    placeholder_path = 'airmozilla/manage/tests/firefox.png'
    placeholder = os.path.basename(placeholder_path)

    def setUp(self):
        super(TestSuggestions, self).setUp()
        self._upload_media(self.placeholder_path)

    def test_suggestions_page(self):
        bob = User.objects.create_user('bob', email='bob@mozilla.com')
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        location = Location.objects.get(id=1)
        SuggestedEvent.objects.create(
            user=bob,
            title='TITLE1',
            slug='SLUG1',
            short_description='SHORT DESCRIPTION1',
            description='DESCRIPTION1',
            start_time=tomorrow,
            location=location,
            placeholder_img=self.placeholder,
            upcoming=True,
            privacy=Event.PRIVACY_CONTRIBUTORS,
            submitted=now,
            first_submitted=now
        )
        SuggestedEvent.objects.create(
            user=bob,
            title='TITLE2',
            slug='SLUG2',
            short_description='SHORT DESCRIPTION2',
            description='DESCRIPTION2',
            start_time=tomorrow,
            location=location,
            placeholder_img=self.placeholder,
            upcoming=False,
            submitted=now - datetime.timedelta(days=1),
            first_submitted=now - datetime.timedelta(days=1),
        )
        event3 = SuggestedEvent.objects.create(
            user=bob,
            title='TITLE3',
            slug='SLUG3',
            short_description='SHORT DESCRIPTION3',
            description='DESCRIPTION3',
            start_time=tomorrow,
            location=location,
            placeholder_img=self.placeholder,
            submitted=now - datetime.timedelta(days=1),
            first_submitted=now - datetime.timedelta(days=1),
            upcoming=False,
            popcorn_url='https://webmaker.org/1234'
        )

        url = reverse('manage:suggestions')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('TITLE1' in response.content)
        ok_('TITLE2' in response.content)
        ok_('TITLE3' in response.content)
        ok_('popcorn' in response.content)

        event3.first_submitted -= datetime.timedelta(days=300)
        event3.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('TITLE1' in response.content)
        ok_('TITLE2' in response.content)
        ok_('TITLE3' not in response.content)

        response = self.client.get(url, {'include_old': 1})
        eq_(response.status_code, 200)
        ok_('TITLE1' in response.content)
        ok_('TITLE2' in response.content)
        ok_('TITLE3' in response.content)

    def test_suggestions_page_states(self):
        bob = User.objects.create_user('bob', email='bob@mozilla.com')
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        location = Location.objects.get(id=1)
        event = SuggestedEvent.objects.create(
            user=bob,
            title='TITLE',
            slug='SLUG',
            short_description='SHORT DESCRIPTION',
            description='DESCRIPTION',
            start_time=tomorrow,
            location=location,
            placeholder_img=self.placeholder,
            privacy=Event.PRIVACY_CONTRIBUTORS,
            submitted=now,
            first_submitted=now
        )
        url = reverse('manage:suggestions')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Submitted' in response.content)

        event.submitted += datetime.timedelta(days=1)
        event.status = SuggestedEvent.STATUS_RESUBMITTED
        event.save()

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('TITLE' in response.content)
        ok_('Resubmitted' in response.content)

        event.review_comments = "Not good"
        event.submitted = None
        event.status = SuggestedEvent.STATUS_REJECTED
        event.save()

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('TITLE' in response.content)
        ok_('Resubmitted' not in response.content)
        ok_('Bounced' in response.content)

        event.submitted = now + datetime.timedelta(seconds=10)
        event.status = SuggestedEvent.STATUS_RESUBMITTED
        event.save()

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('TITLE' in response.content)
        ok_('First submission' not in response.content)
        ok_('Resubmitted' in response.content)
        ok_('Bounced' not in response.content)

    def test_approve_suggested_event_basic(self):
        bob = User.objects.create_user('bob', email='bob@mozilla.com')
        location = Location.objects.get(id=1)
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        tag1 = Tag.objects.create(name='TAG1')
        tag2 = Tag.objects.create(name='TAG2')
        channel = Channel.objects.create(name='CHANNEL')

        # create a suggested event that has everything filled in
        event = SuggestedEvent.objects.create(
            user=bob,
            title='TITLE' * 10,
            slug='SLUG',
            short_description='SHORT DESCRIPTION',
            description='DESCRIPTION',
            start_time=tomorrow,
            location=location,
            placeholder_img=self.placeholder,
            privacy=Event.PRIVACY_CONTRIBUTORS,
            additional_links='ADDITIONAL LINKS',
            remote_presenters='RICHARD & ZANDR',
            submitted=now,
            first_submitted=now,
            popcorn_url='https://',
            call_info='vidyo room',
        )
        event.tags.add(tag1)
        event.tags.add(tag2)
        event.channels.add(channel)

        url = reverse('manage:suggestion_review', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('TITLE' in response.content)
        ok_('SLUG' in response.content)
        ok_('SHORT DESCRIPTION' in response.content)
        ok_('DESCRIPTION' in response.content)
        ok_('ADDITIONAL LINKS' in response.content)
        ok_('RICHARD &amp; ZANDR' in response.content)
        ok_(os.path.basename(self.placeholder) in response.content)
        ok_(location.name in response.content)
        ok_(event.get_privacy_display() in response.content)
        ok_('vidyo room' in response.content)

        response = self.client.post(url)
        eq_(response.status_code, 302)

        # re-load it
        event = SuggestedEvent.objects.get(pk=event.pk)
        real = event.accepted
        assert real
        eq_(real.title, event.title)
        eq_(real.slug, event.slug)
        eq_(real.short_description, event.short_description)
        eq_(real.description, event.description)
        eq_(real.placeholder_img, event.placeholder_img)
        eq_(real.location, location)
        eq_(real.start_time, event.start_time)
        eq_(real.privacy, event.privacy)
        eq_(real.additional_links, event.additional_links)
        eq_(real.remote_presenters, event.remote_presenters)
        eq_(real.popcorn_url, '')
        assert real.tags.all()
        eq_([x.name for x in real.tags.all()],
            [x.name for x in event.tags.all()])
        assert real.channels.all()
        eq_([x.name for x in real.channels.all()],
            [x.name for x in event.channels.all()])

        # it should have sent an email back
        email_sent = mail.outbox[-1]
        eq_(email_sent.recipients(), ['bob@mozilla.com'])
        ok_('accepted' in email_sent.subject)
        ok_('TITLE' in email_sent.subject)
        ok_('TITLE' in email_sent.body)
        # expect the link to the summary is in there
        summary_url = reverse('suggest:summary', args=(event.pk,))
        ok_(summary_url in email_sent.body)

    def test_approve_suggested_event_pre_recorded(self):
        bob = User.objects.create_user('bob', email='bob@mozilla.com')
        location = Location.objects.get(id=1)
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        channel = Channel.objects.create(name='CHANNEL')

        # create a suggested event that has everything filled in
        event = SuggestedEvent.objects.create(
            user=bob,
            title='TITLE' * 10,
            slug='SLUG',
            short_description='SHORT DESCRIPTION',
            description='DESCRIPTION',
            start_time=tomorrow,
            location=location,
            placeholder_img=self.placeholder,
            privacy=Event.PRIVACY_CONTRIBUTORS,
            additional_links='ADDITIONAL LINKS',
            remote_presenters='RICHARD & ZANDR',
            submitted=now,
            first_submitted=now,
            popcorn_url='https://',
            upcoming=False,
        )
        event.channels.add(channel)

        url = reverse('manage:suggestion_review', args=(event.pk,))
        response = self.client.post(url)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('manage:events')
        )
        real = Event.objects.get(title=event.title)
        eq_(real.status, Event.STATUS_PENDING)

    def test_approve_suggested_event_with_default_template_environment(self):
        bob = User.objects.create_user('bob', email='bob@mozilla.com')
        location = Location.objects.get(id=1)
        template = Template.objects.create(name='My Template')
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        channel = Channel.objects.create(name='CHANNEL')

        LocationDefaultEnvironment.objects.create(
            location=location,
            privacy=Event.PRIVACY_COMPANY,
            template=template,
            template_environment={'pri': 'vate'}
        )
        # and another one to make it slightly more challening
        LocationDefaultEnvironment.objects.create(
            location=location,
            privacy=Event.PRIVACY_PUBLIC,
            template=template,
            template_environment={'pub': 'lic'}
        )

        # create a suggested event that has everything filled in
        event = SuggestedEvent.objects.create(
            user=bob,
            title='TITLE' * 10,
            slug='SLUG',
            short_description='SHORT DESCRIPTION',
            description='DESCRIPTION',
            start_time=tomorrow,
            location=location,
            placeholder_img=self.placeholder,
            privacy=Event.PRIVACY_COMPANY,
            additional_links='ADDITIONAL LINKS',
            remote_presenters='RICHARD & ZANDR',
            submitted=now,
            first_submitted=now,
            popcorn_url='https://',
            upcoming=True,
        )
        event.channels.add(channel)

        url = reverse('manage:suggestion_review', args=(event.pk,))
        response = self.client.post(url)
        eq_(response.status_code, 302)
        real = Event.objects.get(title=event.title)
        self.assertRedirects(
            response,
            reverse('manage:event_edit', args=(real.pk,))
        )
        real = Event.objects.get(title=event.title)
        eq_(real.template, template)
        eq_(real.template_environment, {'pri': 'vate'})

    def test_approved_suggested_popcorn_event(self):
        bob = User.objects.create_user('bob', email='bob@mozilla.com')
        location = Location.objects.get(id=1)
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        channel = Channel.objects.create(name='CHANNEL')

        # we need a group that can approve events
        group = Group.objects.create(name='testapprover')
        permission = Permission.objects.get(codename='change_approval')
        group.permissions.add(permission)

        # create a suggested event that has everything filled in
        event = SuggestedEvent.objects.create(
            user=bob,
            title='TITLE' * 10,
            slug='SLUG',
            short_description='SHORT DESCRIPTION',
            description='DESCRIPTION',
            start_time=tomorrow,
            location=location,
            placeholder_img=self.placeholder,
            privacy=Event.PRIVACY_PUBLIC,
            additional_links='ADDITIONAL LINKS',
            remote_presenters='RICHARD & ZANDR',
            upcoming=False,
            popcorn_url='https://goodurl.com/',
            submitted=now,
            first_submitted=now,
        )
        event.channels.add(channel)

        popcorn_template = Template.objects.create(
            name='Popcorn template',
            content='Bla bla',
            default_popcorn_template=True
        )

        url = reverse('manage:suggestion_review', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('TITLE' in response.content)
        ok_('https://goodurl.com' in response.content)

        response = self.client.post(url)
        eq_(response.status_code, 302)

        # re-load it
        event = SuggestedEvent.objects.get(pk=event.pk)
        real = event.accepted
        assert real
        eq_(real.popcorn_url, event.popcorn_url)
        eq_(real.start_time, real.archive_time)
        eq_(real.template, popcorn_template)
        eq_(real.status, Event.STATUS_SCHEDULED)
        # that should NOT have created an Approval instance
        ok_(not Approval.objects.filter(event=real))

    def test_approved_suggested_event_with_discussion(self):
        bob = User.objects.create_user('bob', email='bob@mozilla.com')
        location = Location.objects.get(id=1)
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        channel = Channel.objects.create(name='CHANNEL')

        # create a suggested event that has everything filled in
        event = SuggestedEvent.objects.create(
            user=bob,
            title='TITLE' * 10,
            slug='SLUG',
            short_description='SHORT DESCRIPTION',
            description='DESCRIPTION',
            start_time=tomorrow,
            location=location,
            placeholder_img=self.placeholder,
            privacy=Event.PRIVACY_CONTRIBUTORS,
            additional_links='ADDITIONAL LINKS',
            remote_presenters='RICHARD & ZANDR',
            upcoming=False,
            popcorn_url='https://goodurl.com/',
            submitted=now,
            first_submitted=now,
        )
        event.channels.add(channel)

        richard = User.objects.create(email='richard@mozilla.com')
        discussion = SuggestedDiscussion.objects.create(
            event=event,
            moderate_all=True,
            notify_all=True,
            enabled=True
        )
        discussion.moderators.add(bob)
        discussion.moderators.add(richard)

        url = reverse('manage:suggestion_review', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('TITLE' in response.content)
        ok_('Enabled' in response.content)
        ok_('bob@mozilla.com' in response.content)
        ok_('richard@mozilla.com' in response.content)

        response = self.client.post(url)
        eq_(response.status_code, 302)

        # re-load it
        event = SuggestedEvent.objects.get(pk=event.pk)
        real = event.accepted
        assert real
        eq_(real.popcorn_url, event.popcorn_url)
        eq_(real.start_time, real.archive_time)

        # that should now also have created a discussion
        real_discussion = Discussion.objects.get(event=real)
        ok_(real_discussion.enabled)
        ok_(real_discussion.moderate_all)
        ok_(real_discussion.notify_all)
        ok_(richard in real_discussion.moderators.all())
        ok_(bob in real_discussion.moderators.all())

    def test_approved_suggested_event_with_topics(self):
        bob = User.objects.create_user('bob', email='bob@mozilla.com')
        location = Location.objects.get(id=1)
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        channel = Channel.objects.create(name='CHANNEL')

        # create a suggested event that has everything filled in
        event = SuggestedEvent.objects.create(
            user=bob,
            title='TITLE' * 10,
            slug='SLUG',
            short_description='SHORT DESCRIPTION',
            description='DESCRIPTION',
            start_time=tomorrow,
            location=location,
            placeholder_img=self.placeholder,
            privacy=Event.PRIVACY_PUBLIC,
            additional_links='ADDITIONAL LINKS',
            remote_presenters='RICHARD & ZANDR',
            upcoming=False,
            popcorn_url='https://goodurl.com/',
            submitted=now,
            first_submitted=now,
        )
        event.channels.add(channel)

        topic = Topic.objects.create(
            topic='Money Matters',
            is_active=True
        )
        group = Group.objects.create(name='PR')
        # put some people in that group
        user = User.objects.create_user('jessica', email='jessica@muzilla.com')
        user.groups.add(group)
        topic.groups.add(group)
        event.topics.add(topic)

        url = reverse('manage:suggestion_review', args=(event.pk,))
        response = self.client.post(url)
        eq_(response.status_code, 302)

        # re-load it
        event = SuggestedEvent.objects.get(pk=event.pk)
        real = event.accepted
        assert real.topics.all()

        email_sent = mail.outbox[-2]  # last email goes to the user
        eq_(email_sent.recipients(), ['jessica@muzilla.com'])
        ok_('Approval requested' in email_sent.subject)
        ok_(event.title in email_sent.subject)
        ok_(
            'requires approval from someone in your group' in
            email_sent.body
        )
        ok_(reverse('manage:approvals') in email_sent.body)
        ok_(topic.topic in email_sent.body)

    def test_reject_suggested_event(self):
        bob = User.objects.create_user('bob', email='bob@mozilla.com')
        location = Location.objects.get(id=1)
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        tag1 = Tag.objects.create(name='TAG1')
        tag2 = Tag.objects.create(name='TAG2')
        channel = Channel.objects.create(name='CHANNEL')

        # create a suggested event that has everything filled in
        event = SuggestedEvent.objects.create(
            user=bob,
            title='TITLE',
            slug='SLUG',
            short_description='SHORT DESCRIPTION',
            description='DESCRIPTION',
            start_time=tomorrow,
            location=location,
            placeholder_img=self.placeholder,
            privacy=Event.PRIVACY_CONTRIBUTORS,
            submitted=now,
            first_submitted=now,
        )
        event.tags.add(tag1)
        event.tags.add(tag2)
        event.channels.add(channel)

        url = reverse('manage:suggestion_review', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('TITLE' in response.content)
        ok_('SLUG' in response.content)
        ok_('SHORT DESCRIPTION' in response.content)
        ok_('DESCRIPTION' in response.content)
        ok_(os.path.basename(self.placeholder) in response.content)
        ok_(location.name in response.content)
        ok_(event.get_privacy_display() in response.content)

        data = {'reject': 'true'}
        response = self.client.post(url, data)
        eq_(response.status_code, 200)

        data['review_comments'] = 'You suck!'
        response = self.client.post(url, data)
        eq_(response.status_code, 302)

        # re-load it
        event = SuggestedEvent.objects.get(pk=event.pk)
        ok_(not event.accepted)
        ok_(not event.submitted)
        # still though
        ok_(event.first_submitted)
        eq_(event.status, SuggestedEvent.STATUS_REJECTED)

        # it should have sent an email back
        email_sent = mail.outbox[-1]
        ok_(email_sent.recipients(), ['bob@mozilla.com'])
        ok_('not accepted' in email_sent.subject)
        ok_('TITLE' in email_sent.body)
        ok_('You suck!' in email_sent.body)
        summary_url = reverse('suggest:summary', args=(event.pk,))
        ok_(summary_url in email_sent.body)

    def test_comment_suggested_event(self):
        bob = User.objects.create_user('bob', email='bob@mozilla.com')
        location = Location.objects.get(id=1)
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        tag1 = Tag.objects.create(name='TAG1')
        tag2 = Tag.objects.create(name='TAG2')
        channel = Channel.objects.create(name='CHANNEL')

        # create a suggested event that has everything filled in
        event = SuggestedEvent.objects.create(
            user=bob,
            title='TITLE',
            slug='SLUG',
            short_description='SHORT DESCRIPTION',
            description='DESCRIPTION',
            start_time=tomorrow,
            location=location,
            placeholder_img=self.placeholder,
            privacy=Event.PRIVACY_CONTRIBUTORS,
            submitted=now,
            first_submitted=now,
        )
        event.tags.add(tag1)
        event.tags.add(tag2)
        event.channels.add(channel)

        url = reverse('manage:suggestion_review', args=(event.pk,))
        data = {
            'save_comment': 1,
            'comment': ''
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 200)
        ok_('This field is required' in response.content)
        assert not SuggestedEventComment.objects.all()

        data['comment'] = """
        Hi!
        <script>alert("xss")</script>
        """
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        comment, = SuggestedEventComment.objects.all()
        eq_(comment.comment, data['comment'].strip())
        eq_(comment.user, self.user)  # who I'm logged in as

        # this should have sent an email to bob
        email_sent = mail.outbox[-1]
        ok_(email_sent.recipients(), [bob.email])
        ok_('New comment' in email_sent.subject)
        ok_(event.title in email_sent.subject)
        ok_('<script>alert("xss")</script>' in email_sent.body)
        ok_(reverse('suggest:summary', args=(event.pk,)) in email_sent.body)

    def test_retracted_comments_still_visible_in_management(self):
        bob = User.objects.create_user(
            'bob',
            email='bob@mozilla.com',
            password='secret'
        )
        location = Location.objects.get(id=1)
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        tag1 = Tag.objects.create(name='TAG1')
        tag2 = Tag.objects.create(name='TAG2')
        channel = Channel.objects.create(name='CHANNEL')

        # create a suggested event that has everything filled in
        event = SuggestedEvent.objects.create(
            user=bob,
            title='TITLE',
            slug='SLUG',
            short_description='SHORT DESCRIPTION',
            description='DESCRIPTION',
            start_time=tomorrow,
            location=location,
            placeholder_img=self.placeholder,
            privacy=Event.PRIVACY_CONTRIBUTORS,
            first_submitted=now,
            # Note! No `submitted=now` here
        )
        assert os.path.isfile(event.placeholder_img.path)
        event.tags.add(tag1)
        event.tags.add(tag2)
        event.channels.add(channel)

        url = reverse('manage:suggestions')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.title in response.content)
        event_url = reverse('manage:suggestion_review', args=(event.pk,))
        ok_(event_url in response.content)

        response = self.client.get(event_url)
        eq_(response.status_code, 200)
        ok_('Event is currently not submitted' in response.content)

        # You can't reject or approve it at this stage
        data = {'reject': 'true', 'review_comments': 'Bla'}
        response = self.client.post(event_url, data)
        eq_(response.status_code, 400)

        response = self.client.post(event_url, {})
        eq_(response.status_code, 400)

        # log in as bob
        assert self.client.login(username='bob', password='secret')
        summary_url = reverse('suggest:summary', args=(event.pk,))
        response = self.client.get(summary_url)
        eq_(response.status_code, 200)
        ok_('Your event is no longer submitted' in response.content)
