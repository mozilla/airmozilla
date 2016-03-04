from nose.tools import eq_, ok_

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils.encoding import smart_text

from airmozilla.main.models import (
    Event,
    Tag,
    EventRevision,
    UserProfile,
)
from airmozilla.base.tests.testbase import DjangoTestCase


class TestTooFewTags(DjangoTestCase):

    def test_view_random_event(self):
        url = reverse('main:too_few_tags')
        response = self.client.get(url)
        eq_(response.status_code, 302)

        # let's sign in, as a contributor
        nigel = User.objects.create_user('nigel', 'n@live.in', 'secret')
        UserProfile.objects.create(user=nigel, contributor=True)
        assert self.client.login(username='nigel', password='secret')

        response = self.client.get(url)
        eq_(response.status_code, 200)

        event = Event.objects.get(title='Test event')
        assert not event.tags.all().count()
        content = smart_text(response.content)
        ok_(event.description in content)
        # its event_id should be in there somewhere as a hidden input
        ok_('value="%s"' % event.id in content)

        event.tags.add(Tag.objects.create(name='mytag1'))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        content = smart_text(response.content)
        ok_('value="%s"' % event.id in response.content)

        event.tags.add(Tag.objects.create(name='mytag2'))

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('value="%s"' % event.id not in response.content)
        ok_('Wow!' in response.content)

    def test_view_random_event_private(self):
        url = reverse('main:too_few_tags')

        # let's sign in, as a contributor
        nigel = User.objects.create_user('nigel', 'n@live.in', 'secret')
        UserProfile.objects.create(user=nigel, contributor=True)
        assert self.client.login(username='nigel', password='secret')

        response = self.client.get(url)
        eq_(response.status_code, 200)
        event = Event.objects.get(title='Test event')
        ok_('value="%s"' % event.id in response.content)

        event.privacy = Event.PRIVACY_CONTRIBUTORS
        event.save()
        # still there
        response = self.client.get(url)
        eq_(response.status_code, 200)
        event = Event.objects.get(title='Test event')
        ok_('value="%s"' % event.id in response.content)

        event.privacy = Event.PRIVACY_COMPANY
        event.save()
        # gone!
        response = self.client.get(url)
        eq_(response.status_code, 200)
        event = Event.objects.get(title='Test event')
        ok_('value="%s"' % event.id not in response.content)
        ok_('Wow!' in response.content)

        # become someone else
        User.objects.create_user('r', 'r@example.com', 'secret')
        assert self.client.login(username='r', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        event = Event.objects.get(title='Test event')
        ok_('value="%s"' % event.id in response.content)
        ok_('Wow!' not in response.content)

    def test_make_an_edit(self):
        User.objects.create_user('r', 'r@example.com', 'secret')
        assert self.client.login(username='r', password='secret')
        Tag.objects.create(name='Cake')

        event = Event.objects.get(title='Test event')
        url = reverse('main:too_few_tags')
        response = self.client.post(url, {
            'tags': ',cake, Compilers  , ',
            'event_id': event.id
        })
        eq_(response.status_code, 302)
        # it shouldn't make a new tag for "CAKE"
        eq_(sorted(x.name for x in Tag.objects.all()), ['Cake', 'Compilers'])

        event = Event.objects.get(id=event.id)
        eq_(sorted(x.name for x in event.tags.all()), ['Cake', 'Compilers'])
        base_revision, revision = (
            EventRevision.objects
            .filter(event=event)
            .order_by('created')
        )
        eq_(base_revision.tags.all().count(), 0)
        eq_(sorted(x.name for x in revision.tags.all()), ['Cake', 'Compilers'])

    def test_remove_tag_edit(self):
        User.objects.create_user('r', 'r@example.com', 'secret')
        assert self.client.login(username='r', password='secret')
        tag = Tag.objects.create(name='Cake')

        event = Event.objects.get(title='Test event')
        event.tags.add(tag)

        url = reverse('main:too_few_tags')
        response = self.client.post(url, {
            'tags': ',Compilers  , ',
            'event_id': event.id
        })
        eq_(response.status_code, 302)
        # it shouldn't make a new tag for "CAKE"
        eq_(sorted(x.name for x in Tag.objects.all()), ['Cake', 'Compilers'])

        event = Event.objects.get(id=event.id)
        eq_(sorted(x.name for x in event.tags.all()), ['Compilers'])
        base_revision, revision = (
            EventRevision.objects
            .filter(event=event)
            .order_by('created')
        )
        eq_(sorted(x.name for x in base_revision.tags.all()), ['Cake'])
        eq_(sorted(x.name for x in revision.tags.all()), ['Compilers'])
