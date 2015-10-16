import datetime

from django.core import mail
from django.contrib.auth.models import Group, User
from django.conf import settings
from django.contrib.sites.models import Site
from django.utils import timezone
from django.core.urlresolvers import reverse

from nose.tools import eq_, ok_

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.manage.pestering import pester
from airmozilla.main.models import (
    Approval,
    Event
)


class PesteringTestCase(DjangoTestCase):

    def _age_event_created(self, event, save=True):
        extra_seconds = settings.PESTER_INTERVAL_DAYS * 24 * 60 * 60 + 1
        now = timezone.now()
        event.created = now - datetime.timedelta(seconds=extra_seconds)
        save and event.save()

    def test_nothing_happens(self):
        result = pester()
        ok_(not result)

    def test_sending(self):
        group = Group.objects.create(name='PR Group')
        # we need some people to belong to the group
        bob = User.objects.create(
            username='bob',
            email='bob@example.com',
            is_staff=True
        )
        bob.groups.add(group)
        mr_inactive = User.objects.create(
            username='mr_inactive',
            email='long@gone.com',
            is_staff=True,
            is_active=False,
        )
        mr_inactive.groups.add(group)
        event = Event.objects.get(title='Test event')

        # first pretend that the event was created now
        now = timezone.now()
        event.created = now
        event.save()

        approval = Approval.objects.create(
            event=event,
            group=group,
        )

        site = Site.objects.get_current()
        result = pester(dry_run=True)
        eq_(len(mail.outbox), 0)
        eq_(len(result), 0)

        # nothing because the event is too new
        # let's pretend it's older
        self._age_event_created(event)

        result = pester(dry_run=True)
        eq_(len(mail.outbox), 0)
        eq_(len(result), 1)

        email, subject, message = result[0]
        eq_(email, bob.email)
        ok_('[Air Mozilla]' in subject)
        ok_('1 event' in subject)
        ok_('://%s' % site.domain in message)
        ok_(group.name in message)
        ok_(event.title in message)
        ok_(event.description in message)
        ok_(event.location.name in message)
        ok_(event.location.timezone in message)
        approve_url = reverse('manage:approval_review', args=(approval.pk,))
        ok_(approve_url in message)
        manage_url = reverse('manage:approvals')
        ok_(manage_url in message)

        now = timezone.now()
        assert event.start_time < now
        ok_('Time left: overdue!' in message)

        result = pester()
        # check that 1 email was sent
        eq_(len(mail.outbox), 1)
        email_sent = mail.outbox[-1]
        eq_(email_sent.subject, subject)
        ok_(message in email_sent.body)
        eq_([bob.email], email_sent.recipients())

        # try to send it again and nothing should happen
        result = pester()
        ok_(not result)

        # or force past the caching
        result = pester(force_run=True)
        ok_(result)
        eq_(len(mail.outbox), 2)

    def test_sending_future_event_to_multiple_people(self):
        group = Group.objects.create(name='PR Group')
        group2 = Group.objects.create(name='Hippies')

        # we need some people to belong to the group
        bob = User.objects.create(
            username='bob',
            email='bob@example.com',
            is_staff=True
        )
        bob.groups.add(group)
        steve = User.objects.create(
            username='steve',
            email='steve@example.com',
            is_staff=True
        )
        steve.groups.add(group)
        steve.groups.add(group2)

        now = timezone.now()
        event = Event.objects.get(title='Test event')
        event.start_time = now + datetime.timedelta(hours=1, minutes=1)
        event.save()

        # create a second event
        event2 = Event.objects.create(
            title='Second Title',
            slug='second-title',
            description='Second Event Description',
            start_time=now + datetime.timedelta(days=1, minutes=1),
            status=event.status,
            location=event.location,
            creator=event.creator
        )
        # let's pretend it's older
        self._age_event_created(event)
        self._age_event_created(event2)

        Approval.objects.create(
            event=event,
            group=group,
        )
        Approval.objects.create(
            event=event2,
            group=group2,
        )
        result = pester()
        eq_(len(result), 2)
        eq_(len(mail.outbox), 2)

        for email, subject, message in result:
            ok_('Time left: overdue!' not in message)
            if email == bob.email:
                ok_('1 event to approve' in subject)
                ok_(event.title in message)
                ok_(event2.title not in message)
                ok_(u'Time left: 1\xa0hour' in message)
            elif email == steve.email:
                ok_('2 events to approve' in subject)
                ok_(event.title in message)
                ok_(event2.title in message)
                ok_(u'Time left: 1\xa0day' in message)
            else:
                raise AssertionError(email)
