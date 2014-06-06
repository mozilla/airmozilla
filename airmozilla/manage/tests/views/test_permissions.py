from nose.tools import eq_

from django.conf import settings

from funfactory.urlresolvers import reverse

from .base import ManageTestCase


class TestPermissions(ManageTestCase):
    def test_unauthorized(self):
        """ Client with no log in - should be rejected. """
        self.client.logout()
        response = self.client.get(reverse('manage:home'))
        self.assertRedirects(response, settings.LOGIN_URL
                             + '?next=' + reverse('manage:home'))

    def test_not_staff(self):
        """ User is not staff - should be rejected. """
        self.user.is_staff = False
        self.user.save()
        response = self.client.get(reverse('manage:home'))
        self.assertRedirects(response, settings.LOGIN_URL
                             + '?next=' + reverse('manage:home'))

    def test_staff_home(self):
        """ User is staff - should get an OK homepage. """
        response = self.client.get(reverse('manage:home'))
        eq_(response.status_code, 200)
