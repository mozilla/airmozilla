import json

from nose.tools import eq_, ok_

from django.contrib.auth.models import User, Group
from django.core.urlresolvers import reverse
from django.utils import timezone

from airmozilla.main.views import is_contributor
from airmozilla.main.models import UserProfile
from .base import ManageTestCase


class TestUsersAndGroups(ManageTestCase):

    def test_user_group_pages(self):
        """User and group listing pages respond with success."""
        response = self.client.get(reverse('manage:users'))
        eq_(response.status_code, 200)
        response = self.client.get(reverse('manage:groups'))
        eq_(response.status_code, 200)

    def test_user_edit(self):
        """Add superuser and staff status via the user edit form."""
        user = User.objects.create_user('no', 'no@no.com', 'no')
        url = reverse('manage:user_edit', args=(user.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('no@no.com' in response.content)
        response = self.client.post(
            url,
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

    def test_user_edit_invalid_combinations(self):
        user = User.objects.create_user('no', 'no@no.com', 'no')
        url = reverse('manage:user_edit', kwargs={'id': user.id})
        response = self.client.post(
            url,
            {
                'is_superuser': 'on',
                'is_staff': '',
                'is_active': 'on'
            }
        )
        eq_(response.status_code, 200)
        ok_('Form errors!' in response.content)

        response = self.client.post(
            url,
            {
                'is_superuser': '',
                'is_staff': 'on',
                'is_active': ''
            }
        )
        eq_(response.status_code, 200)
        ok_('Form errors!' in response.content)

        response = self.client.post(
            url,
            {
                'is_superuser': '',
                'is_staff': 'on',
                'is_active': 'on'
            }
        )
        eq_(response.status_code, 200)
        ok_('Form errors!' in response.content)

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

    def test_users_data(self):
        # Because the default user, created from the fixtures,
        # was created without a last_login.
        User.objects.filter(last_login__isnull=True).update(
            last_login=timezone.now()
        )
        assert self.user.last_login
        url = reverse('manage:users_data')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        struct = json.loads(response.content)
        eq_(len(struct['users']), User.objects.all().count())
        ok_('manage:user_edit' in struct['urls'])
        user, = User.objects.filter(is_staff=False)
        assert not is_contributor(user)
        same_user, = [x for x in struct['users'] if x['id'] == user.id]
        ok_(not same_user.get('is_contributor'))
        ok_(not same_user.get('is_superuser'))
        ok_(not same_user.get('is_staff'))
        ok_(not same_user.get('is_inactive'))

        user.is_superuser = True
        user.is_staff = True
        user.is_active = False
        user.save()

        response = self.client.get(url)
        eq_(response.status_code, 200)
        struct = json.loads(response.content)
        same_user, = [x for x in struct['users'] if x['id'] == user.id]
        ok_(same_user.get('is_superuser'))
        ok_(same_user.get('is_staff'))
        ok_(same_user.get('is_inactive'))
        ok_(not same_user.get('groups'))

        testgroup = Group.objects.create(name='testapprover')
        user.groups.add(testgroup)
        response = self.client.get(url)
        eq_(response.status_code, 200)
        struct = json.loads(response.content)
        same_user, = [x for x in struct['users'] if x['id'] == user.id]
        eq_(same_user['groups'], [testgroup.name])

    def test_users_data_contributor(self):
        # Because the default user, created from the fixtures,
        # was created without a last_login.
        User.objects.filter(last_login__isnull=True).update(
            last_login=timezone.now()
        )

        user, = User.objects.filter(username='fake')
        UserProfile.objects.create(
            user=user,
            contributor=True
        )
        assert is_contributor(user)
        url = reverse('manage:users_data')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        struct = json.loads(response.content)
        row = [x for x in struct['users'] if x['email'] == user.email][0]
        ok_(row['is_contributor'])
