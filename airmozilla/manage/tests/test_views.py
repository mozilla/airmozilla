from django.conf import settings
from django.contrib.auth.models import User, Group
from django.test import TestCase

from funfactory.urlresolvers import reverse

from nose.tools import eq_, ok_


class TestPermissions(TestCase):
    def _login(self, is_staff):
        user = User.objects.create_user('fake', 'fake@fake.com', 'fake')
        user.is_staff = is_staff
        user.save()
        assert self.client.login(username='fake', password='fake')
        return user

    def test_unauthorized(self):
        """ Client with no log in - should be rejected. """
        response = self.client.get(reverse('manage.home'))
        self.assertRedirects(response, settings.LOGIN_URL
                             + '?next=' + reverse('manage.home'))

    def test_not_staff(self):
        """ User is not staff - should be rejected. """
        self._login(is_staff=False)
        response = self.client.get(reverse('manage.home'))
        self.assertRedirects(response, settings.LOGIN_URL
                             + '?next=' + reverse('manage.home'))

    def test_staff_home(self):
        """ User is staff - should get an OK homepage. """
        self._login(is_staff=True)
        response = self.client.get(reverse('manage.home'))
        eq_(response.status_code, 200)

    def test_staff_logout(self):
        """ Log out makes admin inaccessible. """
        self._login(is_staff=True)
        self.client.get(reverse('auth.logout'))
        response = self.client.get(reverse('manage.home'))
        self.assertRedirects(response, settings.LOGIN_URL
                             + '?next=' + reverse('manage.home'))

    def test_edit_user(self):
        """ Unprivileged admin - shouldn't see user change page. """
        self._login(is_staff=True)
        response = self.client.get(reverse('manage.users'))
        self.assertRedirects(response, settings.LOGIN_URL
                             + '?next=' + reverse('manage.users'))


class TestUsersAndGroups(TestCase):
    def setUp(self):
        User.objects.create_superuser('fake', 'fake@fake.com', 'fake')
        assert self.client.login(username='fake', password='fake')

    def test_user_edit(self):
        """ Add superuser and staff status via the user edit form. """
        user = User.objects.create_user('no', 'no@no.com', 'no')
        response = self.client.post(reverse('manage.user_edit',
                                            kwargs={'id': user.id}),
            {
                'is_superuser': 'on',
                'is_staff': 'on',
                'is_active': 'on'
            }
        )
        eq_(response.status_code, 302)
        user = User.objects.get(id=user.id)
        ok_(user.is_superuser)
        ok_(user.is_staff)

    def test_group_add(self):
        """ Add a group. """
        response = self.client.post(reverse('manage.group_new'),
            {
                'name': 'fake_group'
            }
        )
        eq_(response.status_code, 302)
        group = Group.objects.get(name='fake_group')
        ok_(group is not None)
        eq_(group.name, 'fake_group')
