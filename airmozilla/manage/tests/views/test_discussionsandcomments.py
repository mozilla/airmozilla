from nose.tools import eq_, ok_

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from airmozilla.main.models import Event
from airmozilla.comments.models import (
    Discussion,
    Comment
)
from .base import ManageTestCase


class TestDiscussionAndComments(ManageTestCase):

    def _create_discussion(self, event, enabled=True, moderate_all=True,
                           notify_all=True):
        return Discussion.objects.create(
            event=event,
            enabled=enabled,
            moderate_all=moderate_all,
            notify_all=notify_all
        )

    def test_create_discussion(self):
        event = Event.objects.get(title='Test event')
        event_edit_url = reverse('manage:event_edit', args=(event.pk,))
        url = reverse('manage:event_discussion', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        response = self.client.post(url, {'cancel': 1})
        eq_(response.status_code, 302)
        self.assertRedirects(response, event_edit_url)

        response = self.client.post(url, {
            'enabled': True,
            'closed': True,
            'notify_all': True,
            'moderate_all': True,
            'moderators': [self.user.pk]
        })
        eq_(response.status_code, 302)
        self.assertRedirects(response, url)

        discussion, = Discussion.objects.all()
        eq_(discussion.event, event)
        ok_(discussion.enabled)
        ok_(discussion.closed)
        ok_(discussion.notify_all)
        ok_(discussion.moderate_all)
        eq_(list(discussion.moderators.all()), [self.user])

        # edit it again
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(self.user.email in response.content)
        response = self.client.post(url, {
            'enabled': True,
            'notify_all': True,
            'moderate_all': True,
            'moderators': [self.user.pk]
        })
        eq_(response.status_code, 302)
        self.assertRedirects(response, url)

        discussion = Discussion.objects.get(pk=discussion.pk)
        eq_(discussion.event, event)
        ok_(discussion.enabled)
        ok_(not discussion.closed)
        ok_(discussion.notify_all)
        ok_(discussion.moderate_all)
        eq_(list(discussion.moderators.all()), [self.user])

        response = self.client.get(url)
        eq_(response.status_code, 200)
        comments_url = reverse('manage:event_comments', args=(event.pk,))
        ok_(comments_url in response.content)

    def test_event_comments(self):
        event = Event.objects.get(title='Test event')
        url = reverse('manage:event_comments', args=(event.pk,))
        self._create_discussion(event)
        response = self.client.get(url)
        eq_(response.status_code, 200)

        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        jay = User.objects.create(username='jay', email='jay@mozilla.com')
        comment1 = Comment.objects.create(
            event=event,
            user=bob,
            comment='First Comment',
            status=Comment.STATUS_POSTED
        )
        comment2 = Comment.objects.create(
            event=event,
            user=bob,
            comment='Second Comment',
            status=Comment.STATUS_APPROVED
        )
        comment3 = Comment.objects.create(
            event=event,
            user=bob,
            comment='Third Comment',
            status=Comment.STATUS_REMOVED
        )
        comment4 = Comment.objects.create(
            event=event,
            user=jay,
            comment='Fourth Comment',
            status=Comment.STATUS_APPROVED,
            flagged=1
        )

        # make sure the event discussion page now loads
        event_discussion_url = reverse(
            'manage:event_discussion',
            args=(event.pk,)
        )
        response = self.client.get(event_discussion_url)
        eq_(response.status_code, 200)

        # and the event_edit page should say there are comments
        event_edit_url = reverse('manage:event_edit', args=(event.pk,))
        response = self.client.get(event_edit_url)
        eq_(response.status_code, 200)
        ok_(event_discussion_url in response.content)
        ok_('4 posted comments' in response.content)

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(comment1.comment in response.content)
        ok_(comment2.comment in response.content)
        ok_(comment3.comment in response.content)
        ok_(comment4.comment in response.content)

        response = self.client.get(url, {'user': 'jay@'})
        eq_(response.status_code, 200)
        ok_(comment1.comment not in response.content)
        ok_(comment2.comment not in response.content)
        ok_(comment3.comment not in response.content)
        ok_(comment4.comment in response.content)

        response = self.client.get(url, {'comment': 'First'})
        eq_(response.status_code, 200)
        ok_(comment1.comment in response.content)
        ok_(comment2.comment not in response.content)
        ok_(comment3.comment not in response.content)
        ok_(comment4.comment not in response.content)

        response = self.client.get(url, {'status': Comment.STATUS_REMOVED})
        eq_(response.status_code, 200)
        ok_(comment1.comment not in response.content)
        ok_(comment2.comment not in response.content)
        ok_(comment3.comment in response.content)
        ok_(comment4.comment not in response.content)

        response = self.client.get(url, {'status': 'flagged'})
        eq_(response.status_code, 200)
        ok_(comment1.comment not in response.content)
        ok_(comment2.comment not in response.content)
        ok_(comment3.comment not in response.content)
        ok_(comment4.comment in response.content)

    def test_all_comments(self):
        event = Event.objects.get(title='Test event')
        event2 = Event.objects.create(
            title='Other event',
            start_time=event.start_time,
            location=event.location,
        )
        url = reverse('manage:all_comments')
        self._create_discussion(event)
        response = self.client.get(url)
        eq_(response.status_code, 200)

        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        jay = User.objects.create(username='jay', email='jay@mozilla.com')
        comment1 = Comment.objects.create(
            event=event,
            user=bob,
            comment='First Comment',
            status=Comment.STATUS_POSTED
        )
        comment2 = Comment.objects.create(
            event=event,
            user=bob,
            comment='Second Comment',
            status=Comment.STATUS_APPROVED
        )
        comment3 = Comment.objects.create(
            event=event2,
            user=bob,
            comment='Third Comment',
            status=Comment.STATUS_REMOVED
        )
        comment4 = Comment.objects.create(
            event=event2,
            user=jay,
            comment='Fourth Comment',
            status=Comment.STATUS_APPROVED,
            flagged=1
        )

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(comment1.comment in response.content)
        ok_(comment2.comment in response.content)
        ok_(comment3.comment in response.content)
        ok_(comment4.comment in response.content)

        response = self.client.get(url, {'user': 'jay@'})
        eq_(response.status_code, 200)
        ok_(comment1.comment not in response.content)
        ok_(comment2.comment not in response.content)
        ok_(comment3.comment not in response.content)
        ok_(comment4.comment in response.content)

        response = self.client.get(url, {'comment': 'First'})
        eq_(response.status_code, 200)
        ok_(comment1.comment in response.content)
        ok_(comment2.comment not in response.content)
        ok_(comment3.comment not in response.content)
        ok_(comment4.comment not in response.content)

        response = self.client.get(url, {'status': Comment.STATUS_REMOVED})
        eq_(response.status_code, 200)
        ok_(comment1.comment not in response.content)
        ok_(comment2.comment not in response.content)
        ok_(comment3.comment in response.content)
        ok_(comment4.comment not in response.content)

        response = self.client.get(url, {'status': 'flagged'})
        eq_(response.status_code, 200)
        ok_(comment1.comment not in response.content)
        ok_(comment2.comment not in response.content)
        ok_(comment3.comment not in response.content)
        ok_(comment4.comment in response.content)

        response = self.client.get(url, {'event': 'OTHER'})
        eq_(response.status_code, 200)
        ok_(comment1.comment not in response.content)
        ok_(comment2.comment not in response.content)
        ok_(comment3.comment in response.content)
        ok_(comment4.comment in response.content)

    def test_comment_edit(self):
        event = Event.objects.get(title='Test event')
        self._create_discussion(event)

        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        comment = Comment.objects.create(
            event=event,
            user=bob,
            comment='First Comment',
            status=Comment.STATUS_POSTED
        )
        url = reverse('manage:comment_edit', args=(comment.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('First Comment' in response.content)

        response = self.client.post(url, {'cancel': 1})
        eq_(response.status_code, 302)
        event_comments_url = reverse('manage:event_comments', args=(event.pk,))
        self.assertRedirects(response, event_comments_url)

        # edit it
        response = self.client.post(url, {
            'comment': 'Really First',
            'flagged': 1,
            'status': Comment.STATUS_APPROVED
        })
        eq_(response.status_code, 302)
        self.assertRedirects(response, url)
        comment = Comment.objects.get(pk=comment.pk)
        eq_(comment.comment, 'Really First')
        eq_(comment.flagged, 1)
        eq_(comment.status, Comment.STATUS_APPROVED)
