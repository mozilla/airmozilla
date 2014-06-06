from nose.tools import eq_, ok_

from django.conf import settings

from funfactory.urlresolvers import reverse

from .base import ManageTestCase


class TestDashboard(ManageTestCase):

    # XXX Using `override_settings` doesn't work because of a bug in `tower`.
    # Once that's fixed start using `override_settings` in the tests instead.
    # @override_settings(ADMINS=(('Bob', 'bob@example.com'),))
    def test_dashboard(self):
        self.user.is_superuser = False
        self.user.save()
        _admins_before = settings.ADMINS
        settings.ADMINS = (('Bob', 'bob@example.com'),)
        try:
            response = self.client.get(reverse('manage:home'))
            eq_(response.status_code, 200)
            ok_('bob@example.com' in response.content)
            # create a superuser
            self.user.is_superuser = True
            assert self.user.email
            self.user.save()
            response = self.client.get(reverse('manage:home'))
            eq_(response.status_code, 200)
            ok_('bob@example.com' not in response.content)
            ok_(self.user.email in response.content)
        finally:
            settings.ADMINS = _admins_before

    def test_cache_busting_headers(self):
        # viewing any of the public pages should NOT have it
        response = self.client.get('/')
        eq_(response.status_code, 200)
        ok_('no-store' not in response.get('Cache-Control', ''))

        response = self.client.get(reverse('manage:home'))
        eq_(response.status_code, 200)
        ok_('no-store' in response['Cache-Control'])
