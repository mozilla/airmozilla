from nose.tools import eq_

from django.test.client import RequestFactory

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.base.helpers import abs_static


class TestAbsStaticHelpers(DjangoTestCase):

    def tearDown(self):
        super(TestAbsStaticHelpers, self).tearDown()

        # This is necessary because funfactory (where we use the static()
        # helper function) uses staticfiles_storage which gets lazy loaded
        # and remembered once in memory.
        # By overriding it like this it means we can change settings
        # and have it reflected immediately
        from funfactory import helpers
        from django.contrib.staticfiles.storage import ConfiguredStorage
        helpers.staticfiles_storage = ConfiguredStorage()
        # cache.clear()

    def test_abs_static(self):
        context = {}
        context['request'] = RequestFactory().get('/')

        result = abs_static(context, 'foo.png')
        eq_(result, 'http://testserver/static/foo.png')

    def test_abs_static_already(self):
        context = {}
        context['request'] = RequestFactory().get('/')

        result = abs_static(context, '/media/foo.png')
        eq_(result, 'http://testserver/media/foo.png')

        result = abs_static(context, '//my.cdn.com/media/foo.png')
        eq_(result, 'http://my.cdn.com/media/foo.png')

    def test_abs_static_with_STATIC_URL(self):
        context = {}
        context['request'] = RequestFactory().get('/')

        with self.settings(STATIC_URL='//my.cdn.com/static/'):
            result = abs_static(context, 'foo.png')
            eq_(result, 'http://my.cdn.com/static/foo.png')

    def test_abs_static_with_already_STATIC_URL(self):
        context = {}
        context['request'] = RequestFactory().get('/')

        with self.settings(STATIC_URL='//my.cdn.com/static/'):
            result = abs_static(context, '//my.cdn.com/static/foo.png')
            eq_(result, 'http://my.cdn.com/static/foo.png')

    def test_abs_static_with_HTTPS_STATIC_URL(self):
        context = {}
        context['request'] = RequestFactory().get('/')

        with self.settings(STATIC_URL='https://my.cdn.com/static/'):
            result = abs_static(context, 'foo.png')
            eq_(result, 'https://my.cdn.com/static/foo.png')

    def test_abs_static_with_STATIC_URL_with_https(self):
        context = {}
        context['request'] = RequestFactory().get('/')
        context['request']._is_secure = lambda: True
        assert context['request'].is_secure()

        with self.settings(STATIC_URL='//my.cdn.com/static/'):
            result = abs_static(context, 'foo.png')
            eq_(result, 'https://my.cdn.com/static/foo.png')
