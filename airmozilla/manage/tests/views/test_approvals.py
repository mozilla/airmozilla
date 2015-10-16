import datetime

from nose.tools import eq_, ok_

from django.contrib.auth.models import User, Group
from django.utils import timezone
from django.core.files import File
from django.core.urlresolvers import reverse

from airmozilla.main.models import Approval, Event, SuggestedEvent, Picture
from .base import ManageTestCase


class TestApprovals(ManageTestCase):

    placeholder = 'airmozilla/manage/tests/firefox.png'

    def test_approvals(self):
        event = Event.objects.get(title='Test event')
        group = Group.objects.create(name='testapprover')
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

    def test_approvals_with_original_suggested_event(self):
        event = Event.objects.get(title='Test event')
        group = Group.objects.create(name='testapprover')
        Approval.objects.create(event=event, group=group)

        self.user.groups.add(group)
        response = self.client.get(reverse('manage:approvals'))
        eq_(response.status_code, 200)
        ok_(event.title in response.content)
        ok_(event.creator.email in response.content)

        # now let's pretend it came from a SuggestedEvent
        bob = User.objects.create(
            username='bob',
            email='bob@mozilla.com',
        )
        suggested_event = SuggestedEvent.objects.create(
            title=event.title,
            slug=event.slug,
            placeholder_img=event.placeholder_img,
            user=bob,
            start_time=event.start_time,
            accepted=event,
        )
        response = self.client.get(reverse('manage:approvals'))
        eq_(response.status_code, 200)
        ok_(event.title in response.content)
        ok_(event.creator.email not in response.content)
        ok_(suggested_event.user.email in response.content)

    def test_approval_review(self):
        event = Event.objects.get(title='Test event')
        group = Group.objects.create(name='testapprover')
        app = Approval.objects.create(event=event, group=group)

        url = reverse('manage:approval_review', kwargs={'id': app.id})
        response_not_in_group = self.client.get(url)
        self.assertRedirects(response_not_in_group,
                             reverse('manage:approvals'))
        User.objects.get(username='fake').groups.add(group)
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_approve = self.client.post(url, {'approve': 'approve'})
        self.assertRedirects(response_approve, reverse('manage:approvals'))
        app = Approval.objects.get(id=app.id)
        ok_(app.approved)
        ok_(app.processed)
        eq_(app.user, User.objects.get(username='fake'))

    def test_approval_review_no_placeholder_img(self):
        event = Event.objects.get(title='Test event')
        group = Group.objects.create(name='testapprover')
        app = Approval.objects.create(event=event, group=group)
        event.placeholder_img = None
        with open(self.placeholder) as fp:
            picture = Picture.objects.create(
                file=File(fp),
            )
            event.picture = picture
            event.save()
        event.picture = picture
        event.save()

        url = reverse('manage:approval_review', kwargs={'id': app.id})
        User.objects.get(username='fake').groups.add(group)
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Picture' in response.content)

    def test_approval_reconsider(self):
        event = Event.objects.get(title='Test event')
        group = Group.objects.create(name='testapprover')
        app = Approval.objects.create(event=event, group=group)
        self.user.groups.add(group)

        url = reverse('manage:approval_review', args=(app.pk,))
        response_approve = self.client.post(url, {
            'approve': 'approve',
            'comment': 'Not good enough'
        })
        self.assertRedirects(response_approve, reverse('manage:approvals'))
        app = Approval.objects.get(id=app.id)
        ok_(app.processed)
        ok_(app.approved)
        eq_(app.comment, 'Not good enough')
        eq_(app.user, User.objects.get(username='fake'))

        # now, let's reconsider
        reconsider_url = reverse('manage:approval_reconsider')
        # missing an id
        response = self.client.post(reconsider_url)
        eq_(response.status_code, 400)
        # junk id
        response = self.client.post(reconsider_url, {'id': 'junk'})
        eq_(response.status_code, 400)
        # not found id
        response = self.client.post(reconsider_url, {'id': '0'})
        eq_(response.status_code, 404)
        # correct id
        response = self.client.post(reconsider_url, {'id': app.pk})
        eq_(response.status_code, 302)

        app = Approval.objects.get(id=app.id)
        ok_(not app.processed)
        ok_(not app.approved)
        eq_(app.comment, '')
        eq_(app.user, User.objects.get(username='fake'))

    def test_approval_review_with_suggested_event(self):
        event = Event.objects.get(title='Test event')
        bob = User.objects.create_user('bob', email='bob@mozilla.com')
        now = timezone.now()
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
        group = Group.objects.create(name='testapprover')
        app = Approval.objects.create(event=event, group=group)

        url = reverse('manage:approval_review', kwargs={'id': app.id})
        response_not_in_group = self.client.get(url)
        self.assertRedirects(response_not_in_group,
                             reverse('manage:approvals'))
        User.objects.get(username='fake').groups.add(group)
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Originally requested by' in response.content)
        ok_(bob.email in response.content)
