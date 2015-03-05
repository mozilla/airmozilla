from nose.tools import eq_

from django.contrib.auth.models import User, AnonymousUser
from django.test import TestCase
from django.test.client import RequestFactory
from django.conf import settings

from funfactory.urlresolvers import reverse

from airmozilla.main.models import Event, UserProfile
from airmozilla.main.context_processors import (
    browserid,
    autocompeter,
)


class TestBrowserID(TestCase):

    def test_redirect_next(self):
        request = RequestFactory().get('/some/page/')
        result = browserid(request)['redirect_next']()
        eq_(result, '/some/page/')

        request = RequestFactory().get('/some/page/?next=/other/page/')
        result = browserid(request)['redirect_next']()
        eq_(result, '/other/page/')

    def test_redirect_next_exceptions(self):
        request = RequestFactory().get(reverse('main:login'))
        result = browserid(request)['redirect_next']()
        eq_(result, '/')

        request = RequestFactory().get(reverse('main:login_failure'))
        result = browserid(request)['redirect_next']()
        eq_(result, '/')

    def test_redirect_invalid_next(self):
        next = 'http://www.peterbe.com'
        request = RequestFactory().get('/some/page/?next=%s' % next)
        result = browserid(request)['redirect_next']()
        eq_(result, '/')


class TestAutocompeter(TestCase):

    def setUp(self):
        super(TestAutocompeter, self).setUp()
        settings.AUTOCOMPETER_KEY = 'somethingrandomlooking'

    def test_autocompeter_disabled(self):
        request = RequestFactory().get('/')
        request.user = AnonymousUser()
        with self.settings(AUTOCOMPETER_KEY=None):
            result = autocompeter(request)
            eq_(result, {})

    def test_autocompeter_anonymous(self):
        request = RequestFactory().get('/')
        request.user = AnonymousUser()
        result = autocompeter(request)
        eq_(result['autocompeter_groups'], '')

    def test_autocompeter_employee(self):
        request = RequestFactory().get('/')
        request.user = User.objects.create(
            username='employee'
        )
        result = autocompeter(request)
        eq_(
            result['autocompeter_groups'],
            '%s,%s' % (Event.PRIVACY_CONTRIBUTORS, Event.PRIVACY_COMPANY)
        )

    def test_autocompeter_contributor(self):
        request = RequestFactory().get('/')
        request.user = User.objects.create(
            username='contributor'
        )
        UserProfile.objects.create(
            user=request.user,
            contributor=True,
        )
        result = autocompeter(request)
        eq_(
            result['autocompeter_groups'],
            '%s' % (Event.PRIVACY_CONTRIBUTORS,)
        )

    def test_autocompeter_different_domain(self):
        request = RequestFactory().get('/')
        request.user = AnonymousUser()
        result = autocompeter(request)
        eq_(result['autocompeter_domain'], '')
        with self.settings(AUTOCOMPETER_DOMAIN='airmo'):
            result = autocompeter(request)
            eq_(result['autocompeter_domain'], 'airmo')

    def test_autocompeter_different_url(self):
        request = RequestFactory().get('/')
        request.user = AnonymousUser()
        result = autocompeter(request)
        # this has a default in tests
        eq_(result['autocompeter_url'], settings.AUTOCOMPETER_URL)
        with self.settings(AUTOCOMPETER_URL='http://autocompeter.dev/v1'):
            result = autocompeter(request)
            eq_(result['autocompeter_url'], 'http://autocompeter.dev/v1')
