from nose.tools import eq_
import mock

from django.conf import settings
from django.contrib.auth.models import User, Group, Permission
from django.core.urlresolvers import reverse

from airmozilla.main.models import UserProfile, Event, CuratedGroup
from airmozilla.base.tests.test_mozillians import (
    Response,
    VOUCHED_FOR_USERS,
    NO_USERS,
)
from .base import ManageTestCase


class TestPermissions(ManageTestCase):
    def test_unauthorized(self):
        """ Client with no log in - should be rejected. """
        self.client.logout()
        response = self.client.get(reverse('manage:dashboard'))
        self.assertRedirects(response, settings.LOGIN_URL +
                             '?next=' + reverse('manage:dashboard'))

    def test_not_staff(self):
        """ User is not staff - should be rejected. """
        self.user.is_staff = False
        self.user.save()
        response = self.client.get(reverse('manage:dashboard'))
        self.assertRedirects(response, settings.LOGIN_URL +
                             '?next=' + reverse('manage:dashboard'))

    def test_staff_home(self):
        """ User is staff - should get an OK homepage. """
        response = self.client.get(reverse('manage:dashboard'))
        eq_(response.status_code, 200)

    @mock.patch('requests.get')
    def test_editing_events_with_curated_groups(self, rget):

        calls = []

        def mocked_get(url, **options):
            calls.append(url)
            if 'peterbe' in url:
                if 'group=badasses' in url:
                    return Response(NO_USERS)
                if 'group=swedes':
                    return Response(VOUCHED_FOR_USERS)
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        self.client.logout()
        assert self.client.get(reverse('manage:dashboard')).status_code == 302

        # now log in as a contributor
        contributor = User.objects.create_user(
            'peter', 'peterbe@gmail.com', 'secret'
        )

        producers = Group.objects.create(name='Producer')
        change_event_permission = Permission.objects.get(
            codename='change_event'
        )
        change_event_others_permission = Permission.objects.get(
            codename='change_event_others'
        )
        producers.permissions.add(change_event_permission)
        producers.permissions.add(change_event_others_permission)
        contributor.groups.add(producers)
        contributor.is_staff = True
        contributor.save()

        UserProfile.objects.create(
            user=contributor,
            contributor=True
        )
        assert self.client.login(username='peter', password='secret')

        event = Event.objects.get(title='Test event')
        assert event.privacy == Event.PRIVACY_PUBLIC
        url = reverse('manage:event_edit', args=(event.id,))

        response = self.client.get(url)
        eq_(response.status_code, 200)

        # the contributor producer can't view it if it's private
        event.privacy = Event.PRIVACY_COMPANY
        event.save()
        response = self.client.get(url)
        eq_(response.status_code, 302)

        # but it's ok if it's for contributors
        event.privacy = Event.PRIVACY_CONTRIBUTORS
        event.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # but not if the event is only open to certain curated groups
        curated_group = CuratedGroup.objects.create(
            event=event,
            name='badasses'
        )
        response = self.client.get(url)
        eq_(response.status_code, 302)

        curated_group.delete()
        CuratedGroup.objects.create(
            event=event,
            name='swedes'
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)

        assert len(calls) == 2, calls
