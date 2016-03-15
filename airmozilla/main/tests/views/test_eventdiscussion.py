from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils.encoding import smart_text

from nose.tools import eq_, ok_

from airmozilla.main.models import Event, EventOldSlug
from airmozilla.comments.models import Discussion
from airmozilla.base.tests.testbase import DjangoTestCase


class TestEventDiscussion(DjangoTestCase):

    def test_link_to_it(self):
        event = Event.objects.get(title='Test event')
        event_url = reverse('main:event', args=(event.slug,))
        edit_url = reverse('main:event_edit', args=(event.slug,))
        response = self.client.get(event_url)
        url = reverse('main:event_discussion', args=(event.slug,))
        eq_(response.status_code, 200)
        ok_(url not in response.content)
        ok_(edit_url not in response.content)

        # let's sign in
        user = self._login()
        response = self.client.get(event_url)
        eq_(response.status_code, 200)
        response_content = response.content.decode('utf-8')
        # still not!
        ok_(url not in response_content)
        ok_(edit_url in response_content)

        event.creator = user
        event.save()
        response = self.client.get(event_url)
        eq_(response.status_code, 200)
        response_content = response.content.decode('utf-8')
        # still not because there's no discussion set up
        ok_(url not in response_content)
        ok_(edit_url in response_content)

        Discussion.objects.create(event=event)
        response = self.client.get(event_url)
        eq_(response.status_code, 200)
        response_content = response.content.decode('utf-8')
        ok_(url in response_content)
        ok_(edit_url in response_content)

    def test_permission_access(self):
        event = Event.objects.get(title='Test event')
        event.privacy = Event.PRIVACY_COMPANY
        event.save()
        EventOldSlug.objects.create(
            slug='old-slug',
            event=event
        )
        bad_url = reverse('main:event_discussion', args=('old-slug',))
        response = self.client.get(bad_url)
        eq_(response.status_code, 302)

        url = reverse('main:event_discussion', args=(event.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 302)

        user = self._login()
        response = self.client.get(url)
        eq_(response.status_code, 302)

        event.creator = user
        event.save()
        response = self.client.get(url)
        eq_(response.status_code, 302)

        response = self.client.post(url, {'any': 'thing'})
        eq_(response.status_code, 302)

        discussion = Discussion.objects.create(
            event=event,
            enabled=True
        )
        discussion.moderators.add(user)
        discussion.moderators.add(
            User.objects.create(email='richard@example.com')
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        emails = [user.email, 'richard@example.com']
        ok_(', '.join(emails) in smart_text(response.content))

        # Now let's try to post something to it
        data = {
            'enabled': True,
            'closed': True,
            'notify_all': True,
            'moderate_all': True,
            'moderators': (', '.join(emails)).upper()
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        # should have worked
        discussion = Discussion.objects.get(
            id=discussion.id,
            enabled=True,
            closed=True,
            notify_all=True,
            moderate_all=True,
        )
        eq_(
            sorted(x.email for x in discussion.moderators.all()),
            emails
        )

        # try to send a moderator email address we don't know about
        response = self.client.post(url, dict(
            data,
            moderators='xxx@example.com'
        ))
        eq_(response.status_code, 200)
        ok_(
            'xxx@example.com does not exist as a Air Mozilla user'
            in response.content
        )
        response = self.client.post(url, dict(
            data,
            moderators=', ,\n,,'
        ))
        eq_(response.status_code, 200)
        ok_(
            'You must have at least one moderator'
            in response.content
        )

        # cancel this time
        response = self.client.post(url, dict(
            data,
            moderators=', ,\n,,',
            cancel=''
        ))
        eq_(response.status_code, 302)
