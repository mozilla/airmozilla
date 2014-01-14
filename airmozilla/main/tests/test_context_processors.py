from nose.tools import eq_

from django.test import TestCase
from django.test.client import RequestFactory

from funfactory.urlresolvers import reverse

from airmozilla.main.context_processors import browserid


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
