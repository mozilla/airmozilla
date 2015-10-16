from nose.tools import eq_, ok_

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from airmozilla.manage import related

from airmozilla.main.models import (
    Event,
    Tag,
    UserProfile,
)

from airmozilla.base.tests.testbase import DjangoTestCase


class RelatedTestCase(DjangoTestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']
    main_image = 'airmozilla/manage/tests/firefox.png'

    def setUp(self):
        super(RelatedTestCase, self).setUp()
        related.flush()

    def test_related_public(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        # events similar but with different tags
        other = Event.objects.create(
            title='Mozilla Event',
            description='bla bla',
            status=event.status,
            start_time=event.start_time,
            archive_time=event.archive_time,
            privacy=event.privacy,
            placeholder_img=event.placeholder_img,
            )
        tag1 = Tag.objects.create(name='SomeTag')
        event.tags.add(tag1)
        tag2 = Tag.objects.create(name='PartyTag')
        other.tags.add(tag2)
        related.index(all=True)

        url = reverse('main:related_content', args=(event.slug,))
        response = self.client.get(url)
        ok_('Mozilla Event' in response.content)

    def test_unrelated_privacy(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        # events with different privacies and logged in
        other = Event.objects.create(
            title='Happiness event',
            description='bla bla',
            status=event.status,
            start_time=event.start_time,
            archive_time=event.archive_time,
            privacy=Event.PRIVACY_COMPANY,
            placeholder_img=event.placeholder_img,
            )
        tag1 = Tag.objects.create(name='SomeTag')
        event.tags.add(tag1)
        other.tags.add(tag1)
        related.index(all=True)

        self._login()

        url = reverse('main:related_content', args=(event.slug,))
        response = self.client.get(url)
        ok_('Hapiness event' not in response.content)

    # more tests for multiple types of users
    def test_related_content_logged_users(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        # events similar with use logged-in
        other = Event.objects.create(
            title='Event test',
            description='bla bla',
            status=event.status,
            start_time=event.start_time,
            archive_time=event.archive_time,
            privacy=event.privacy,
            placeholder_img=event.placeholder_img,
            )

        tag1 = Tag.objects.create(name='SomeTag')
        other.tags.add(tag1)
        event.tags.add(tag1)
        related.index(all=True)

        self._login()

        url = reverse('main:related_content', args=(event.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Event test' in response.content)

        User.objects.create_user(
            'helen', 'helen@mozilla.com', 'secret'
        )
        assert self.client.login(username='helen', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Event test' in response.content)

        contributor = User.objects.create_user(
            'nigel', 'nigel@live.com', 'secret'
        )
        UserProfile.objects.create(
            user=contributor,
            contributor=True
        )
        assert self.client.login(username='nigel', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Event test' in response.content)

    def test_unrelated_users(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        # events that are dissimilar in tags and title
        other = Event.objects.create(
            title='Mozilla Festival',
            description='bla bla',
            status=event.status,
            start_time=event.start_time,
            archive_time=event.archive_time,
            privacy=Event.PRIVACY_PUBLIC,
            placeholder_img=event.placeholder_img,
            )
        tag1 = Tag.objects.create(name='SomeTag')
        event.tags.add(tag1)
        tag2 = Tag.objects.create(name='PartyTag')
        other.tags.add(tag2)
        related.index(all=True)

        url = reverse('main:related_content', args=(event.slug,))
        response = self.client.get(url)
        ok_('Mozilla Festival' not in response.content)

        User.objects.create_user(
            'gloria', 'gloria@mozilla.com', 'starlight'
        )
        assert self.client.login(username='gloria', password='starlight')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Mozilla Festival' not in response.content)

        contributor = User.objects.create_user(
            'nigel', 'nigel@live.com', 'secret'
        )
        UserProfile.objects.create(
            user=contributor,
            contributor=True
        )
        assert self.client.login(username='nigel', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Mozilla Festival' not in response.content)

    def test_unrelated_privacy_company(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        # events with privacy company i.e staff
        other = Event.objects.create(
            title='Happiness event',
            description='bla bla',
            status=event.status,
            start_time=event.start_time,
            archive_time=event.archive_time,
            privacy=Event.PRIVACY_COMPANY,
            placeholder_img=event.placeholder_img,
            )
        tag1 = Tag.objects.create(name='SomeTag')
        event.tags.add(tag1)
        other.tags.add(tag1)
        related.index(all=True)

        url = reverse('main:related_content', args=(event.slug,))
        response = self.client.get(url)
        ok_('Happiness event' not in response.content)

        User.objects.create_user(
            'gloria', 'gloria@mozilla.com', 'starlight'
        )
        assert self.client.login(username='gloria', password='starlight')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Happiness event' in response.content)

        contributor = User.objects.create_user(
            'nigel', 'nigel@live.com', 'secret'
        )
        UserProfile.objects.create(
            user=contributor,
            contributor=True
        )
        assert self.client.login(username='nigel', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Happiness event' not in response.content)

    def test_unrelated_privacy_contributor(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        # events with privacy contributors
        other = Event.objects.create(
            title='Happiness event',
            description='bla bla',
            status=event.status,
            start_time=event.start_time,
            archive_time=event.archive_time,
            privacy=Event.PRIVACY_CONTRIBUTORS,
            placeholder_img=event.placeholder_img,
            )
        tag1 = Tag.objects.create(name='SomeTag')
        event.tags.add(tag1)
        other.tags.add(tag1)
        related.index(all=True)

        url = reverse('main:related_content', args=(event.slug,))
        response = self.client.get(url)
        ok_('Happiness event' not in response.content)

        User.objects.create_user(
            'gloria', 'gloria@mozilla.com', 'starlight'
        )
        assert self.client.login(username='gloria', password='starlight')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Happiness event' in response.content)

        contributor = User.objects.create_user(
            'nigel', 'nigel@live.com', 'secret'
        )
        UserProfile.objects.create(
            user=contributor,
            contributor=True
        )
        assert self.client.login(username='nigel', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Happiness event' in response.content)

    def test_related_event_remove(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        # events similar but with different tags
        other = Event.objects.create(
            title='Mozilla Event',
            description='bla bla',
            status=event.STATUS_REMOVED,
            start_time=event.start_time,
            archive_time=event.archive_time,
            privacy=event.privacy,
            placeholder_img=event.placeholder_img,
            )
        tag1 = Tag.objects.create(name='SomeTag')
        event.tags.add(tag1)
        other.tags.add(tag1)
        related.index(all=True)

        url = reverse('main:related_content', args=(event.slug,))
        response = self.client.get(url)
        ok_('Mozilla Event' not in response.content)

        User.objects.create_user(
            'gloria', 'gloria@mozilla.com', 'starlight'
        )
        assert self.client.login(username='gloria', password='starlight')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Mozilla Festival' not in response.content)

        contributor = User.objects.create_user(
            'nigel', 'nigel@live.com', 'secret'
        )
        UserProfile.objects.create(
            user=contributor,
            contributor=True
        )
        assert self.client.login(username='nigel', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Mozilla Festival' not in response.content)
