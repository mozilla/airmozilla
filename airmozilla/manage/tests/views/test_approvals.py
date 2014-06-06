import datetime

from nose.tools import eq_, ok_

from django.contrib.auth.models import User, Group
from django.utils.timezone import utc

from funfactory.urlresolvers import reverse

from airmozilla.main.models import Approval, Event, SuggestedEvent
from .base import ManageTestCase


class TestApprovals(ManageTestCase):

    placeholder = 'airmozilla/manage/tests/firefox.png'

    def test_approvals(self):
        event = Event.objects.get(title='Test event')
        group = Group.objects.get(name='testapprover')
        Approval.objects.create(event=event, group=group)

        response = self.client.get(reverse('manage:approvals'))
        eq_(response.status_code, 200)
        # if you access the approvals page without belonging to any group
        # you'll get a warning alert
        ok_('You are not a member of any group' in response.content)
        ok_('Test event' not in response.content)

        # belong to a group
        self.user.groups.add(group)
        response = self.client.get(reverse('manage:approvals'))
        eq_(response.status_code, 200)
        ok_('You are not a member of any group' not in response.content)
        ok_('Test event' in response.content)

        # but it shouldn't appear if it's removed
        event.status = Event.STATUS_REMOVED
        event.save()
        response = self.client.get(reverse('manage:approvals'))
        eq_(response.status_code, 200)
        ok_('Test event' not in response.content)

    def test_approval_review(self):
        event = Event.objects.get(title='Test event')
        group = Group.objects.get(name='testapprover')
        app = Approval.objects.create(event=event, group=group)

        url = reverse('manage:approval_review', kwargs={'id': app.id})
        response_not_in_group = self.client.get(url)
        self.assertRedirects(response_not_in_group,
                             reverse('manage:approvals'))
        User.objects.get(username='fake').groups.add(1)
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_approve = self.client.post(url, {'approve': 'approve'})
        self.assertRedirects(response_approve, reverse('manage:approvals'))
        app = Approval.objects.get(id=app.id)
        ok_(app.approved)
        ok_(app.processed)
        eq_(app.user, User.objects.get(username='fake'))

    def test_approval_review_with_suggested_event(self):
        event = Event.objects.get(title='Test event')
        bob = User.objects.create_user('bob', email='bob@mozilla.com')
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        tomorrow = now + datetime.timedelta(days=1)
        SuggestedEvent.objects.create(
            user=bob,
            accepted=event,
            title='TITLE',
            slug='SLUG',
            short_description='SHORT DESCRIPTION',
            description='DESCRIPTION',
            start_time=tomorrow,
            location=event.location,
            placeholder_img=self.placeholder,
            privacy=Event.PRIVACY_PUBLIC,
            submitted=now,
        )
        group = Group.objects.get(name='testapprover')
        app = Approval.objects.create(event=event, group=group)

        url = reverse('manage:approval_review', kwargs={'id': app.id})
        response_not_in_group = self.client.get(url)
        self.assertRedirects(response_not_in_group,
                             reverse('manage:approvals'))
        User.objects.get(username='fake').groups.add(1)
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Originally requested by' in response.content)
        ok_(bob.email in response.content)
