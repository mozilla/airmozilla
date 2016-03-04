from nose.tools import eq_

from django.test.client import RequestFactory

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.base.templatetags.jinja_helpers import (
    abs_static,
    show_duration,
)


class TestAbsStaticHelpers(DjangoTestCase):

    def tearDown(self):
        super(TestAbsStaticHelpers, self).tearDown()

        # This is necessary because airmozilla.base.utils (where we use
        # the static() helper function) uses staticfiles_storage which
        # gets lazy loaded and remembered once in memory.
        # By overriding it like this it means we can change settings
        # and have it reflected immediately
        # from django.conf import settings
        # print settings.STATICFILES_STORAGE
        from airmozilla.base import utils
        from django.contrib.staticfiles.storage import ConfiguredStorage
        utils.staticfiles_storage = ConfiguredStorage()

    def test_abs_static(self):
        """
        Normally in your templates you do something like this:

            <img src="{{ static('images/logo.png') }}">

        and it'll yield something like this:

            <img src="/static/images/logo.png">

        But if you really want to make it absolute you do this:

            <img src="{{ abs_static('images/logo.png') }}">

        and it should yield something like:

            <img src="https://example.com/static/images/logo.png">

        """
        context = {}
        context['request'] = RequestFactory().get('/')

        absolute_relative_path = self._create_static_file('foo.png', 'data')
        result = abs_static(context, 'foo.png')
        eq_(result, 'http://testserver%s' % absolute_relative_path)

    # def test_abs_static_already(self):
    #     context = {}
    #     context['request'] = RequestFactory().get('/')
    #
    #     absolute_relative_path = self._create_static_file('bar.png', 'data')
    #
    #     result = abs_static(context, 'bar.png')
    #     # print ('absolute_relative_path', absolute_relative_path)
    #     eq_(result, 'http://testserver%s' % absolute_relative_path)
    #
    #     result = abs_static(context, '//my.cdn.com/bar.png')
    #     eq_(result, 'http://my.cdn.com/media/bar.png')

    def test_abs_static_with_STATIC_URL(self):
        context = {}
        context['request'] = RequestFactory().get('/')

        absolute_relative_path = self._create_static_file('bob.png', 'data')

        with self.settings(STATIC_URL='//my.cdn.com/static/'):
            result = abs_static(context, 'bob.png')
            eq_(result, 'http://my.cdn.com%s' % absolute_relative_path)

    # def test_abs_static_with_already_STATIC_URL(self):
    #     context = {}
    #     context['request'] = RequestFactory().get('/')
    #
    #     absolute_relative_path = self._create_static_file('hi.png', 'data')
    #
    #     with self.settings(STATIC_URL='//my.cdn.com/static/'):
    #         result = abs_static(context, '//my.cdn.com/static/foo.png')
    #         eq_(result, 'http://my.cdn.com/static/foo.png')

    def test_abs_static_with_HTTPS_STATIC_URL(self):
        context = {}
        context['request'] = RequestFactory().get('/')

        absolute_relative_path = self._create_static_file('hoo.png', 'data')

        with self.settings(STATIC_URL='https://my.cdn.com/static/'):
            result = abs_static(context, 'hoo.png')
            eq_(result, 'https://my.cdn.com%s' % absolute_relative_path)

    def test_abs_static_with_STATIC_URL_with_https(self):
        context = {}
        context['request'] = RequestFactory().get('/')
        context['request'].is_secure = lambda: True
        assert context['request'].is_secure()

        absolute_relative_path = self._create_static_file('foo.png', 'data')

        with self.settings(STATIC_URL='//my.cdn.com/static/'):
            result = abs_static(context, 'foo.png')
            eq_(result, 'https://my.cdn.com%s' % absolute_relative_path)


class TestDuration(DjangoTestCase):

    def test_show_duration_long_format(self):
        result = show_duration(60 * 60)
        eq_(result, "1 hour")

        result = show_duration(60)
        eq_(result, "1 minute")

        result = show_duration(2 * 60 * 60 + 10 * 60)
        eq_(result, "2 hours 10 minutes")

        result = show_duration(1 * 60 * 60 + 1 * 60)
        eq_(result, "1 hour 1 minute")

        result = show_duration(1 * 60 * 60 + 1 * 60 + 1)
        eq_(result, "1 hour 1 minute")

        result = show_duration(2 * 60 * 60 + 2 * 60)
        eq_(result, "2 hours 2 minutes")

        result = show_duration(1 * 60 * 60 + 1 * 60 + 1, include_seconds=True)
        eq_(result, "1 hour 1 minute 1 second")

        result = show_duration(1 * 60 * 60 + 1 * 60 + 2, include_seconds=True)
        eq_(result, "1 hour 1 minute 2 seconds")

        result = show_duration(49)
        eq_(result, "49 seconds")

        result = show_duration(66.61)
        eq_(result, '1 minute')

        result = show_duration(66.61, include_seconds=True)
        eq_(result, '1 minute 6 seconds')
