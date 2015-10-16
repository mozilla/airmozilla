import datetime

from nose.tools import eq_, ok_

from django.contrib.auth.models import User, Group
from django.core import mail
from django.test.client import RequestFactory
from django.utils import timezone
from django.core.urlresolvers import reverse

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.manage import sending
from airmozilla.main.models import (
    Event,
    SuggestedEvent,
    SuggestedEventComment,
    Location,
    Approval
)


class TestSending(DjangoTestCase):

    def test_email_about_suggestion_comment(self):
        user, = User.objects.all()[:1]
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        location = Location.objects.get(id=1)

        suggested_event = SuggestedEvent.objects.create(
            user=user,
            title='TITLE',
            slug='SLUG',
            short_description='SHORT DESCRIPTION',
            description='DESCRIPTION',
            start_time=tomorrow,
            location=location,
            placeholder_img=self.main_image,
            privacy=Event.PRIVACY_CONTRIBUTORS,
            first_submitted=now,
        )
        comment = SuggestedEventComment.objects.create(
            comment="Bla bla",
            user=user,
            suggested_event=suggested_event
        )
        request = RequestFactory().get('/')
        bob = User.objects.create(email='bob@mozilla.com')
        sending.email_about_suggestion_comment(comment, bob, request)
        email_sent = mail.outbox[-1]
        ok_(email_sent.alternatives)
        eq_(email_sent.recipients(), [user.email])
        ok_('TITLE' in email_sent.subject)
        ok_('TITLE' in email_sent.body)
        summary_url = reverse('suggest:summary', args=(suggested_event.pk,))
        ok_(summary_url in email_sent.body)

    def test_email_about_accepted_suggestion(self):
        user, = User.objects.all()[:1]
        event, = Event.objects.all()[:1]
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        location = Location.objects.get(id=1)

        suggested_event = SuggestedEvent.objects.create(
            user=user,
            title='TITLE',
            slug='SLUG',
            short_description='SHORT DESCRIPTION',
            description='DESCRIPTION',
            start_time=tomorrow,
            location=location,
            placeholder_img=self.main_image,
            privacy=Event.PRIVACY_CONTRIBUTORS,
            first_submitted=now,
            submitted=now,
            accepted=event,
        )
        suggested_event.accepted = event
        suggested_event.save()

        request = RequestFactory().get('/')
        sending.email_about_accepted_suggestion(
            suggested_event,
            event,
            request
        )
        email_sent = mail.outbox[-1]
        ok_(email_sent.alternatives)
        eq_(email_sent.recipients(), [user.email])
        ok_('Requested event accepted' in email_sent.subject)
        ok_(event.title in email_sent.subject)
        ok_('TITLE' in email_sent.body)
        summary_url = reverse('suggest:summary', args=(suggested_event.pk,))
        ok_(summary_url in email_sent.body)

    def test_email_about_rejected_suggestion(self):
        # user = User.objects.create(email='richard@mozilla.com')
        user, = User.objects.all()[:1]
        # event, = Event.objects.all()[:1]
        # comment = Comment.objects.create(
        #     event=event,
        #     user=user,
        #     comment='Bla Bla',
        #     status=Comment.STATUS_APPROVED
        # )
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        location = Location.objects.get(id=1)

        suggested_event = SuggestedEvent.objects.create(
            user=user,
            title='TITLE',
            slug='SLUG',
            short_description='SHORT DESCRIPTION',
            description='DESCRIPTION',
            start_time=tomorrow,
            location=location,
            placeholder_img=self.main_image,
            privacy=Event.PRIVACY_CONTRIBUTORS,
            first_submitted=now,
            submitted=now,
            review_comments='Not Good Enough'
        )

        request = RequestFactory().get('/')
        bob = User.objects.create(email='bob@mozilla.com')
        sending.email_about_rejected_suggestion(
            suggested_event,
            bob,
            request
        )
        email_sent = mail.outbox[-1]
        ok_(email_sent.alternatives)
        eq_(email_sent.recipients(), [user.email])
        ok_('TITLE' in email_sent.subject)
        ok_('TITLE' in email_sent.body)
        ok_('Not Good Enough' in email_sent.body)
        summary_url = reverse('suggest:summary', args=(suggested_event.pk,))
        ok_(summary_url in email_sent.body)

    def test_email_about_approval_requested(self):
        group = Group.objects.create(name='testapprover')

        event, = Event.objects.all()[:1]
        Approval.objects.create(event=event, group=group)
        request = RequestFactory().get('/')
        sending.email_about_approval_requested(
            event,
            group,
            request
        )
        ok_(not mail.outbox)
        # because no users belong to the group
        bob = User.objects.create(email='bob@mozilla.com')
        bob.groups.add(group)
        sending.email_about_approval_requested(
            event,
            group,
            request
        )
        email_sent = mail.outbox[-1]
        ok_(email_sent.alternatives)
        eq_(email_sent.recipients(), [bob.email])
        ok_(event.title in email_sent.subject)
        ok_(event.title in email_sent.body)
        ok_(group.name in email_sent.body)
        ok_(event.creator.email in email_sent.body)
        ok_(reverse('manage:approvals') in email_sent.body)
