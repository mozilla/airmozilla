from nose.tools import eq_, ok_

from django.contrib.auth.models import User, Group

from funfactory.urlresolvers import reverse

from airmozilla.main.models import UserProfile
from .base import ManageTestCase


class TestUsersAndGroups(ManageTestCase):

    def test_user_group_pages(self):
        """User and group listing pages respond with success."""
        response = self.client.get(reverse('manage:users'))
        eq_(response.status_code, 200)
        response = self.client.get(reverse('manage:users'), {'page': 5000})
        eq_(response.status_code, 200)
        response = self.client.get(reverse('manage:groups'))
        eq_(response.status_code, 200)

    def test_users_contributors(self):
        user = User.objects.create_user('yes', 'yes@yes.com', 'yes')
        UserProfile.objects.create(
            user=user,
            contributor=True
        )
        response = self.client.get(reverse('manage:users'))
        eq_(response.status_code, 200)
        ok_('Contributor' in response.content)

    def test_user_edit(self):
        """Add superuser and staff status via the user edit form."""
        user = User.objects.create_user('no', 'no@no.com', 'no')
        response = self.client.post(
            reverse('manage:user_edit', kwargs={'id': user.id}),
            {
                'is_superuser': 'on',
                'is_staff': 'on',
                'is_active': 'on'
            }
        )

        self.assertRedirects(response, reverse('manage:users'))
        user = User.objects.get(id=user.id)
        ok_(user.is_superuser)
        ok_(user.is_staff)

    def test_group_add(self):
        """Add a group and verify its creation."""
        response = self.client.get(reverse('manage:group_new'))
        eq_(response.status_code, 200)
        response = self.client.post(
            reverse('manage:group_new'),
            {
                'name': 'fake_group'
            }
        )
        self.assertRedirects(response, reverse('manage:groups'))
        group = Group.objects.get(name='fake_group')
        ok_(group is not None)
        eq_(group.name, 'fake_group')

    def test_group_edit(self):
        """Group editing: group name change form sucessfully changes name."""
        group, __ = Group.objects.get_or_create(name='testergroup')
        response = self.client.get(reverse('manage:group_edit',
                                           kwargs={'id': group.id}))
        eq_(response.status_code, 200)
        response = self.client.post(
            reverse('manage:group_edit', kwargs={'id': group.id}),
            {
                'name': 'newtestergroup  '
            }
        )
        self.assertRedirects(response, reverse('manage:groups'))
        group = Group.objects.get(id=group.id)
        eq_(group.name, 'newtestergroup')

    def test_group_remove(self):
        group, __ = Group.objects.get_or_create(name='testergroup')
        self._delete_test(group, 'manage:group_remove', 'manage:groups')

    def test_user_search(self):
        """Searching for a created user redirects properly; otherwise fail."""
        user = User.objects.create_user('t', 'testuser@mozilla.com')
        response_ok = self.client.get(
            reverse('manage:users'),
            {
                'email': user.email
            }
        )
        self.assertRedirects(
            response_ok,
            reverse('manage:user_edit', kwargs={'id': user.id})
        )
        response_fail = self.client.post(
            reverse('manage:users'),
            {
                'email': 'bademail@mozilla.com'
            }
        )
        eq_(response_fail.status_code, 200)
