import re
import smtplib
import urlparse

from nose.tools import ok_, eq_
import mock

from django.conf import settings
from django.utils import timezone
from django.core import mail
from django.core.files import File
from django.contrib.sites.models import Site
from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse

from sorl.thumbnail import get_thumbnail

from airmozilla.main.models import (
    Event,
    EventEmail,
    Picture,
    UserProfile,
    Approval
)
from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.new import eventemails


class TestEventEmails(DjangoTestCase):
    sample_jpg = 'airmozilla/manage/tests/presenting.jpg'

    def test_basic_send(self):
        event = Event.objects.get(title='Test event')
        assert event.status == Event.STATUS_SCHEDULED
        with open(self.sample_jpg) as fp:
            picture = Picture.objects.create(
                event=event,
                file=File(fp),
            )
        event.picture = picture
        event.created = timezone.now()
        event.save()

        attempted, successful, skipped = eventemails.send_new_event_emails()
        eq_(attempted, 1)
        eq_(successful, 1)
        eq_(skipped, 0)

        email_sent = mail.outbox[-1]
        ok_(event.title in email_sent.subject)
        ok_(settings.EMAIL_FROM_ADDRESS in email_sent.from_email)
        ok_(event.creator.email in email_sent.recipients())

        html_body, _ = email_sent.alternatives[0]

        # assertions against the plaintext body are hard because
        view_url = reverse('main:event', args=(event.slug,))
        ok_(view_url in html_body)
        edit_url = reverse('main:event_edit', args=(event.slug,))
        ok_(edit_url in html_body)
        for channel in event.channels.all():
            channel_url = reverse('main:home_channels', args=(channel.slug,))
            ok_(channel_url in html_body)

        # except there to be a full URL to the image
        thumb = get_thumbnail(
            event.picture.file,
            '385x218',
            crop='center'
        )
        image_url = 'https://{0}{1}'.format(
            Site.objects.get_current().domain,
            thumb.url
        )
        ok_(image_url in html_body)

        # you try again, and this time it should not send
        attempted, successful, skipped = eventemails.send_new_event_emails()
        eq_(attempted, 0)
        eq_(successful, 0)
        eq_(skipped, 0)
        eq_(len(mail.outbox), 1)

        sent, = EventEmail.objects.filter(event=event)
        eq_(sent.user, event.creator)
        eq_(sent.to, event.creator.email)
        eq_(sent.send_failure, None)

    def test_dont_send(self):
        event = Event.objects.get(title='Test event')
        attempted, _, _ = eventemails.send_new_event_emails()
        eq_(attempted, 0)

        # The reason nothing is sent is because the event was created
        # a long time ago.
        event.created = timezone.now()
        assert event.creator.email
        event.save()
        group = Group.objects.create(name='PR')
        approval = Approval.objects.create(
            event=event,
            group=group
        )
        attempted, _, _ = eventemails.send_new_event_emails()
        eq_(attempted, 0)

        approval.approved = True
        approval.processed = True
        approval.save()
        assert not event.needs_approval()
        assert event in Event.objects.all().approved()
        event.status = Event.STATUS_PENDING
        event.save()
        attempted, _, _ = eventemails.send_new_event_emails()
        eq_(attempted, 0)

        event.status = Event.STATUS_SCHEDULED
        event.save()
        assert event in Event.objects.scheduled().approved()
        attempted, successful, _ = eventemails.send_new_event_emails()
        eq_(attempted, 1)
        eq_(attempted, 1)

    @mock.patch('airmozilla.new.sending.EmailMultiAlternatives')
    def test_failure_to_send(self, p_ema):
        event = Event.objects.get(title='Test event')
        event.created = timezone.now()
        assert event.creator.email
        event.save()

        # def mocked_EmailMultiAlternatives(*args, **kwargs):
        # p_ema.side_effect = mocked_EmailMultiAlternatives
        p_ema().send.side_effect = smtplib.SMTPRecipientsRefused('crap!')

        attempted, successful, skipped = eventemails.send_new_event_emails()
        eq_(attempted, 1)
        eq_(successful, 0)
        eq_(skipped, 0)

        sent, = EventEmail.objects.filter(event=event)
        eq_(sent.user, event.creator)
        eq_(sent.to, event.creator.email)
        ok_('crap!' in sent.send_failure)
        ok_('SMTPRecipientsRefused' in sent.send_failure)

    def test_dont_send_on_optout(self):
        event = Event.objects.get(title='Test event')
        event.created = timezone.now()
        assert event.creator.email
        event.save()
        UserProfile.objects.create(
            user=event.creator,
            optout_event_emails=True
        )

        attempted, successful, skipped = eventemails.send_new_event_emails()
        eq_(attempted, 0)
        eq_(successful, 0)
        eq_(skipped, 1)

    def test_opt_out(self):
        event = Event.objects.get(title='Test event')
        event.created = timezone.now()
        assert event.creator.email
        event.save()

        attempted, successful, skipped = eventemails.send_new_event_emails()
        eq_(attempted, 1)
        eq_(successful, 1)
        eq_(skipped, 0)

        email_sent = mail.outbox[-1]
        # need to extract the unsubscribe link from in there
        html_body, _ = email_sent.alternatives[0]
        unsubscribe_link, = [
            x for x in re.findall('href="(.*?)"', html_body)
            if x.count('/unsubscribe/')
        ]
        unsubscribe_link = urlparse.urlparse(unsubscribe_link).path
        # let's go there
        response = self.client.get(unsubscribe_link)
        eq_(response.status_code, 200)
        # let's hit it
        response = self.client.post(unsubscribe_link)
        self.assertRedirects(response, reverse('new:unsubscribed'))

        user_profile, = UserProfile.objects.filter(user=event.creator)
        ok_(user_profile.optout_event_emails)

    def test_opt_out_invalid_link(self):
        event = Event.objects.get(title='Test event')
        event.created = timezone.now()
        assert event.creator.email
        event.save()

        attempted, successful, skipped = eventemails.send_new_event_emails()
        eq_(attempted, 1)
        eq_(successful, 1)
        eq_(skipped, 0)

        email_sent = mail.outbox[-1]
        # need to extract the unsubscribe link from in there
        html_body, _ = email_sent.alternatives[0]
        unsubscribe_link, = [
            x for x in re.findall('href="(.*?)"', html_body)
            if x.count('/unsubscribe/')
        ]
        unsubscribe_link = urlparse.urlparse(unsubscribe_link).path
        # mess with it
        unsubscribe_link = re.sub('\d', '0', unsubscribe_link)
        # let's go there
        response = self.client.get(unsubscribe_link)
        eq_(response.status_code, 200)
        ok_('Sorry' in response.content)
        # let's hit it
        response = self.client.post(unsubscribe_link)
        eq_(response.status_code, 400)
