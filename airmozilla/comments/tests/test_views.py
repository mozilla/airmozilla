import calendar
import json
import re
import uuid

import mock

from django.core.cache import cache
from django.contrib.auth.models import User
from django.core import mail
from django.core.urlresolvers import reverse

from nose.tools import eq_, ok_

from airmozilla.main.models import Event
from airmozilla.base.tests.testbase import Response, DjangoTestCase
from airmozilla.comments.views import (
    can_manage_comments,
    get_latest_comment
)
from airmozilla.comments.models import (
    Discussion,
    Comment,
    Unsubscription
)
from airmozilla.base.tests.test_mozillians import (
    VOUCHED_FOR_USERS,
    VOUCHED_FOR,
)


class TestComments(DjangoTestCase):

    def _create_discussion(self, event, enabled=True, moderate_all=True,
                           notify_all=True):
        return Discussion.objects.create(
            event=event,
            enabled=enabled,
            moderate_all=moderate_all,
            notify_all=notify_all
        )

    def test_can_manage_comments(self):
        event = Event.objects.get(title='Test event')

        jay = User.objects.create(username='jay', email='jay@mozilla.com')
        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        richard = User.objects.create(username='richard',
                                      email='richard@mozilla.com',
                                      is_superuser=True)
        discussion = self._create_discussion(event)
        discussion.moderators.add(jay)

        ok_(not can_manage_comments(bob, discussion))
        ok_(can_manage_comments(jay, discussion))
        ok_(can_manage_comments(richard, discussion))

    def test_get_latest_comment(self):
        event = Event.objects.get(title='Test event')
        eq_(get_latest_comment(event), None)
        # or by ID
        eq_(get_latest_comment(event.pk), None)

        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        comment = Comment.objects.create(
            event=event,
            user=bob,
            comment="Hi, it's Bob",
            status=Comment.STATUS_POSTED
        )
        latest = get_latest_comment(event)
        eq_(latest, None)
        latest = get_latest_comment(event, include_posted=True)
        modified = calendar.timegm(comment.modified.utctimetuple())
        eq_(latest, modified)
        # again, or by event ID
        latest_second_time = get_latest_comment(event.pk, include_posted=True)
        eq_(latest, latest_second_time)

    def test_basic_event_data(self):
        event = Event.objects.get(title='Test event')
        # render the event and there should be no comments
        url = reverse('main:event', args=(event.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Comments' not in response.content)

        # if not enabled you get that back in JSON
        comments_url = reverse('comments:event_data', args=(event.pk,))
        response = self.client.get(comments_url)
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        eq_(structure['discussion']['enabled'], False)

        # also, trying to post a comment when it's not enable
        # should cause an error
        response = self.client.post(comments_url, {
            'name': 'Peter',
            'comment': 'Bla bla'
        })
        eq_(response.status_code, 400)

        # enable discussion
        discussion = self._create_discussion(event)
        jay = User.objects.create(username='jay', email='jay@mozilla.com')
        discussion.moderators.add(jay)

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Comments' in response.content)

        comments_url = reverse('comments:event_data', args=(event.pk,))
        response = self.client.get(comments_url)
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        eq_(structure['discussion']['enabled'], True)
        eq_(structure['discussion']['closed'], False)
        ok_('No comments posted' in structure['html'])

        # even though it's enabled, it should reject postings
        # because we're not signed in
        response = self.client.post(comments_url, {
            'name': 'Peter',
            'comment': 'Bla bla'
        })
        eq_(response.status_code, 403)

        # so, let's sign in and try again
        User.objects.create_user('richard', password='secret')
        # but it should be ok if self.user had the add_event permission
        assert self.client.login(username='richard', password='secret')
        response = self.client.post(comments_url, {
            'name': 'Richard',
            'comment': 'Bla bla'
        })
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        ok_('No comments posted' not in structure['html'])
        ok_('Bla bla' in structure['html'])

        comment = Comment.objects.get(comment='Bla bla')
        ok_(comment)
        eq_(comment.status, Comment.STATUS_POSTED)

        # the moderator should now have received an email
        email_sent = mail.outbox[-1]
        ok_(event.title in email_sent.subject)
        ok_('requires moderation' in email_sent.subject)

        ok_(url in email_sent.body)
        ok_(url + '#comment-%d' % comment.pk in email_sent.body)

    def test_post_comment_no_moderation(self):
        event = Event.objects.get(title='Test event')
        self._create_discussion(event, moderate_all=False)
        User.objects.create_user('richard', password='secret')
        assert self.client.login(username='richard', password='secret')
        comments_url = reverse('comments:event_data', args=(event.pk,))
        response = self.client.post(comments_url, {
            'name': 'Richard',
            'comment': 'Bla bla'
        })
        eq_(response.status_code, 200)
        # structure = json.loads(response.content)
        comment = Comment.objects.get(event=event)
        eq_(comment.status, Comment.STATUS_APPROVED)

    def test_moderation_immediately(self):
        """when you post a comment that needs moderation, the moderator
        can click a link in the email notification that immediately
        approves the comment without being signed in"""
        event = Event.objects.get(title='Test event')
        discussion = self._create_discussion(event)
        jay = User.objects.create(username='jay', email='jay@mozilla.com')
        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        discussion.moderators.add(jay)
        comment = Comment.objects.create(
            event=event,
            user=bob,
            comment='Bla bla',
            status=Comment.STATUS_POSTED
        )
        identifier = uuid.uuid4().hex[:10]
        cache.set('approve-%s' % identifier, comment.pk, 60)
        cache.set('remove-%s' % identifier, comment.pk, 60)
        approve_url = reverse(
            'comments:approve_immediately',
            args=(identifier, comment.pk)
        )
        remove_url = reverse(
            'comments:remove_immediately',
            args=(identifier, comment.pk)
        )
        response = self.client.get(approve_url)
        eq_(response.status_code, 200)
        ok_('Comment Approved' in response.content)

        # reload
        comment = Comment.objects.get(pk=comment.pk)
        eq_(comment.status, Comment.STATUS_APPROVED)

        response = self.client.get(remove_url)
        eq_(response.status_code, 200)
        ok_('Comment Removed' in response.content)

        # reload
        comment = Comment.objects.get(pk=comment.pk)
        eq_(comment.status, Comment.STATUS_REMOVED)

        # try with identifiers that aren't in the cache
        bogus_identifier = uuid.uuid4().hex[:10]
        bogus_approve_url = reverse(
            'comments:approve_immediately',
            args=(bogus_identifier, comment.pk)
        )
        bogus_remove_url = reverse(
            'comments:remove_immediately',
            args=(bogus_identifier, comment.pk)
        )

        response = self.client.get(bogus_approve_url)
        eq_(response.status_code, 200)
        ok_('Comment Approved' not in response.content)
        ok_('Unable to Approve Comment' in response.content)

        response = self.client.get(bogus_remove_url)
        eq_(response.status_code, 200)
        ok_('Comment Removed' not in response.content)
        ok_('Unable to Remove Comment' in response.content)

    def test_unsubscribe_on_reply_notifications(self):
        event = Event.objects.get(title='Test event')
        discussion = self._create_discussion(event)
        jay = User.objects.create(username='jay', email='jay@mozilla.com')
        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        discussion.moderators.add(jay)
        comment = Comment.objects.create(
            event=event,
            user=bob,
            comment='Bla bla',
            status=Comment.STATUS_APPROVED
        )
        jay.set_password('secret')
        jay.save()
        assert self.client.login(username='jay', password='secret')
        # post a reply
        url = reverse('comments:event_data', args=(event.pk,))
        response = self.client.post(url, {
            'comment': 'I think this',
            'name': 'Jay',
            'reply_to': comment.pk,
        })
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        ok_('Bla bla' in structure['html'])
        ok_('I think this' in structure['html'])

        # now, we must approve this comment
        new_comment = Comment.objects.get(
            comment='I think this',
            user=jay
        )
        response = self.client.post(url, {
            'approve': new_comment.pk,
        })
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        eq_(structure, {'ok': True})

        email_sent = mail.outbox[-1]
        ok_('Reply' in email_sent.subject)
        ok_(event.title in email_sent.subject)
        eq_(email_sent.to, ['bob@mozilla.com'])
        # expect there to be two unsubscribe links in there
        url_unsubscribe = re.findall(
            '/comments/unsubscribe/\w{10}/\d+/',
            email_sent.body
        )[0]
        urls_unsubscribe_all = re.findall(
            '/comments/unsubscribe/\w{10}/',
            email_sent.body
        )
        for url in urls_unsubscribe_all:
            if not url_unsubscribe.startswith(url):
                url_unsubscribe_all = url
        self.client.logout()

        # now let's visit these
        response = self.client.get(url_unsubscribe)
        eq_(response.status_code, 200)
        ok_('Are you sure' in response.content)

        response = self.client.post(url_unsubscribe, {})
        eq_(response.status_code, 302)
        Unsubscription.objects.get(
            user=bob,
            discussion=discussion
        )
        unsubscribed_url = reverse(
            'comments:unsubscribed',
            args=(discussion.pk,)
        )
        ok_(unsubscribed_url in response['location'])
        response = self.client.get(unsubscribed_url)
        eq_(response.status_code, 200)
        ok_('Unsubscribed' in response.content)
        ok_(event.title in response.content)

        response = self.client.post(url_unsubscribe_all, {})
        eq_(response.status_code, 302)
        Unsubscription.objects.get(
            user=bob,
            discussion__isnull=True
        )
        unsubscribed_url = reverse('comments:unsubscribed_all')
        ok_(unsubscribed_url in response['location'])

    def test_unsubscribed_reply_notifications_discussion(self):
        event = Event.objects.get(title='Test event')
        discussion = self._create_discussion(event)
        jay = User.objects.create(username='jay', email='jay@mozilla.com')
        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        discussion.moderators.add(jay)
        comment = Comment.objects.create(
            event=event,
            user=bob,
            comment='Bla bla',
            status=Comment.STATUS_APPROVED
        )

        Unsubscription.objects.create(
            user=bob,
            discussion=discussion
        )

        jay.set_password('secret')
        jay.save()
        assert self.client.login(username='jay', password='secret')
        # post a reply
        url = reverse('comments:event_data', args=(event.pk,))
        response = self.client.post(url, {
            'comment': 'I think this',
            'reply_to': comment.pk,
        })
        eq_(response.status_code, 200)
        # But it needs to be approved for reply notifications to
        # even be attempted.
        new_comment = Comment.objects.get(comment='I think this')
        eq_(new_comment.reply_to.user, bob)
        response = self.client.post(url, {
            'approve': new_comment.pk,
        })
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        eq_(structure, {'ok': True})

        ok_(not mail.outbox)

    def test_unsubscribed_reply_notifications_all(self):
        event = Event.objects.get(title='Test event')
        discussion = self._create_discussion(event)
        jay = User.objects.create(username='jay', email='jay@mozilla.com')
        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        discussion.moderators.add(jay)
        comment = Comment.objects.create(
            event=event,
            user=bob,
            comment='Bla bla',
            status=Comment.STATUS_APPROVED
        )

        Unsubscription.objects.create(
            user=bob,
        )

        jay.set_password('secret')
        jay.save()
        assert self.client.login(username='jay', password='secret')
        # post a reply
        url = reverse('comments:event_data', args=(event.pk,))
        response = self.client.post(url, {
            'comment': 'I think this',
            'reply_to': comment.pk,
        })
        eq_(response.status_code, 200)
        # But it needs to be approved for reply notifications to
        # even be attempted.
        new_comment = Comment.objects.get(comment='I think this')
        eq_(new_comment.reply_to.user, bob)
        response = self.client.post(url, {
            'approve': new_comment.pk,
        })

        ok_(not mail.outbox)

    def test_invalid_reply_to(self):
        event = Event.objects.get(title='Test event')
        discussion = self._create_discussion(event)
        jay = User.objects.create(username='jay', email='jay@mozilla.com')
        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        discussion.moderators.add(jay)
        Comment.objects.create(
            event=event,
            user=bob,
            comment='Bla bla',
            status=Comment.STATUS_APPROVED
        )

        jay.set_password('secret')
        jay.save()
        assert self.client.login(username='jay', password='secret')
        # post a reply
        url = reverse('comments:event_data', args=(event.pk,))
        response = self.client.post(url, {
            'comment': 'I think this',
            'reply_to': '999999999',
        })
        eq_(response.status_code, 400)

    @mock.patch('logging.error')
    @mock.patch('requests.get')
    def test_fetch_user_name(self, rget, rlogging):
        cache.clear()

        def mocked_get(url, **options):
            if '/v2/users/99999' in url:
                return Response(VOUCHED_FOR)
            if 'peterbe' in url:
                return Response(VOUCHED_FOR_USERS)
            raise NotImplementedError(url)
        rget.side_effect = mocked_get

        url = reverse('comments:user_name')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        eq_(structure['name'], '')

        peterbe = User.objects.create_user(
            username='peterbe', password='secret'
        )
        assert self.client.login(username='peterbe', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        eq_(structure['name'], '')

        peterbe.email = 'peterbe@mozilla.com'
        peterbe.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        eq_(structure['name'], 'Peter Bengtsson')

    def test_modify_comment_without_permission(self):
        event = Event.objects.get(title='Test event')
        self._create_discussion(event)

        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        comment = Comment.objects.create(
            event=event,
            user=bob,
            comment='Bla bla',
            status=Comment.STATUS_POSTED
        )

        url = reverse('comments:event_data', args=(event.pk,))
        response = self.client.post(url, {
            'approve': comment.pk,
        })
        eq_(response.status_code, 403)

        # and not being logged in you definitely can't post comments
        response = self.client.post(url, {
            'comment': "My opinion",
        })
        eq_(response.status_code, 403)

        User.objects.create_user(username='jay', password='secret')
        assert self.client.login(username='jay', password='secret')

        response = self.client.post(url, {
            'approve': comment.pk,
        })
        eq_(response.status_code, 403)

        response = self.client.post(url, {
            'unapprove': comment.pk,
        })
        eq_(response.status_code, 403)

        response = self.client.post(url, {
            'remove': comment.pk,
        })
        eq_(response.status_code, 403)

        # but you can flag
        response = self.client.post(url, {
            'flag': comment.pk,
        })
        eq_(response.status_code, 200)

        # but not unflag
        response = self.client.post(url, {
            'unflag': comment.pk,
        })
        eq_(response.status_code, 403)

    def test_modify_comment_with_permission(self):
        event = Event.objects.get(title='Test event')
        discussion = self._create_discussion(event)

        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        jay = User.objects.create_user(username='jay', password='secret')
        discussion.moderators.add(jay)

        comment = Comment.objects.create(
            event=event,
            user=bob,
            comment='Bla bla',
            status=Comment.STATUS_POSTED,
            flagged=1
        )

        url = reverse('comments:event_data', args=(event.pk,))
        assert self.client.login(username='jay', password='secret')

        response = self.client.post(url, {
            'approve': comment.pk,
        })
        eq_(response.status_code, 200)
        ok_(Comment.objects.get(status=Comment.STATUS_APPROVED))

        response = self.client.post(url, {
            'unapprove': comment.pk,
        })
        eq_(response.status_code, 200)
        ok_(Comment.objects.get(status=Comment.STATUS_POSTED))

        response = self.client.post(url, {
            'remove': comment.pk,
        })
        eq_(response.status_code, 200)
        ok_(Comment.objects.get(status=Comment.STATUS_REMOVED))

        response = self.client.post(url, {
            'unflag': comment.pk,
        })
        eq_(response.status_code, 200)
        ok_(Comment.objects.get(flagged=0))

    def test_event_data_latest_400(self):
        cache.clear()
        event = Event.objects.get(title='Test event')
        url = reverse('comments:event_data_latest', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 400)
        discussion = self._create_discussion(event)
        discussion.enabled = False
        discussion.save()
        response = self.client.get(url)
        eq_(response.status_code, 400)

    def test_event_data_latest(self):
        event = Event.objects.get(title='Test event')
        self._create_discussion(event)
        url = reverse('comments:event_data_latest', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        eq_(structure['latest_comment'], None)

        bob = User.objects.create(username='bob', email='bob@mozilla.com')
        comment = Comment.objects.create(
            user=bob,
            event=event,
            comment="Hi, it's Bob",
            status=Comment.STATUS_POSTED
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        eq_(structure['latest_comment'], None)

        response = self.client.get(url, {'include_posted': True})
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        modified = calendar.timegm(comment.modified.utctimetuple())
        eq_(structure['latest_comment'], modified)
        # ask it again and it should be the same
        response_second = self.client.get(url, {'include_posted': True})
        eq_(response_second.status_code, 200)
        eq_(response.content, response_second.content)
