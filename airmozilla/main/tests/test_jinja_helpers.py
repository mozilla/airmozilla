# -*- coding: utf-8 -*-

import uuid
import shutil
import os

import mock
from nose.tools import eq_, ok_
import jinja2

from django.conf import settings
from django.db.utils import IntegrityError
from django.test.client import RequestFactory
from django.core.files import File
from django.core.urlresolvers import reverse

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.main.models import Event, Picture
from airmozilla.main.templatetags.jinja_helpers import (
    thumbnail,
    get_thumbnail,
    pluralize,
    short_desc,
    truncate_words,
    truncate_chars,
    safe_html,
    make_absolute,
    show_thumbnail,
    show_lazyr_thumbnail,
)


class TestThumbnailHelper(DjangoTestCase):

    def setUp(self):

        sample_file = os.path.join(
            os.path.dirname(__file__),
            'animage.png'
        )
        assert os.path.isfile(sample_file)
        if not os.path.isdir(settings.MEDIA_ROOT):
            os.mkdir(settings.MEDIA_ROOT)

        self.destination = os.path.join(
            settings.MEDIA_ROOT,
            uuid.uuid4().hex + '.png'
        )
        shutil.copyfile(sample_file, self.destination)

    def tearDown(self):
        if os.path.isfile(self.destination):
            os.remove(self.destination)

    def test_thumbnail(self):
        nailed = thumbnail(os.path.basename(self.destination), '10x10')
        eq_(nailed.width, 10)
        # we don't want these lying around in local install
        nailed.delete()

    @mock.patch('airmozilla.main.templatetags.jinja_helpers.time')
    @mock.patch('airmozilla.main.templatetags.jinja_helpers.get_thumbnail')
    def test_thumbnail_with_some_integrityerrors(
        self,
        mocked_get_thumbnail,
        mocked_time
    ):

        runs = []

        def proxy(*args, **kwargs):
            runs.append(args)
            if len(runs) < 3:
                raise IntegrityError('bla')
            return get_thumbnail(*args, **kwargs)

        mocked_get_thumbnail.side_effect = proxy

        nailed = thumbnail(os.path.basename(self.destination), '10x10')
        eq_(nailed.width, 10)
        # we don't want these lying around in local install
        nailed.delete()


class TestShowThumbnailHelper(DjangoTestCase):

    def test_show_thumbnail(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        html = show_thumbnail(event, geometry='111x99')
        ok_('width="111"' in html)
        ok_('height="99"' in html)
        ok_('alt="%s"' % event.title in html)
        # suppose the event has a picture now

        with open(self.main_image) as fp:
            picture = Picture.objects.create(file=File(fp))
            event.picture = picture
            event.save()

        new_html = show_thumbnail(event, geometry='111x99')
        ok_(new_html != html)
        ok_('width="111"' in new_html)
        ok_('height="99"' in new_html)
        ok_('alt="%s"' % event.title in new_html)

    def test_show_lazyr_thumbnail(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)

        html = show_lazyr_thumbnail(event)
        ok_('data-layzr=' not in html)
        eq_(html, show_thumbnail(event))

        with open(self.main_image) as fp:
            Picture.objects.create(
                file=File(fp),
                default_placeholder=True
            )

        html = show_lazyr_thumbnail(event, geometry='111x99')
        ok_('data-layzr=' in html)


class TestPluralizer(DjangoTestCase):

    def test_pluralize(self):
        eq_(pluralize(1), '')
        eq_(pluralize(0), 's')
        eq_(pluralize(2), 's')

        eq_(pluralize(1, 'ies'), '')
        eq_(pluralize(0, 'ies'), 'ies')
        eq_(pluralize(2, 'ies'), 'ies')


class FauxEvent(object):
    def __init__(self, description, short_description):
        self.description = description
        self.short_description = short_description


class TestTruncation(DjangoTestCase):

    def test_short_desc(self):
        event = FauxEvent(
            'Some Long Description',
            'Some Short Description'
        )
        result = short_desc(event)
        eq_(result, 'Some Short Description')

        # no short description
        event = FauxEvent(
            'Some Long Description',
            ''
        )
        result = short_desc(event)
        eq_(result, 'Some Long Description')

    def test_strip_description_html(self):
        event = FauxEvent(
            'Hacking with <script>alert(xss)</script>',
            ''
        )
        result = short_desc(event)
        eq_(result, 'Hacking with <script>alert(xss)</script>')

        result = short_desc(event, strip_html=True)
        eq_(result, 'Hacking with alert(xss)')

    def test_truncated_short_description(self):
        event = FauxEvent(
            'Word ' * 50,
            ''
        )
        result = short_desc(event, words=10)
        eq_(result, ('Word ' * 10).strip() + '...')

    def test_truncate_words(self):
        result = truncate_words('peter Bengtsson', 1)
        eq_(result, 'peter...')

    def test_truncate_chars(self):
        result = truncate_chars('peter bengtsson', 11)
        eq_(result, 'peter beng' + u'…')
        result = truncate_chars('peter bengtsson', 10)
        eq_(result, 'peter ben' + u'…')
        result = truncate_chars('peter bengtsson', 7)
        eq_(result, 'peter' + u'…')

    def test_truncate_chars_too_short(self):
        self.assertRaises(
            AssertionError,
            truncate_chars,
            'peter', 4
        )


class SafeHTML(DjangoTestCase):

    def test_basics(self):
        text = ''
        result = safe_html(text)
        ok_(isinstance(result, jinja2.Markup))
        eq_(result, '')

    def test_allowed_html(self):
        text = '<p>This <a href="http://peterbe.com">is</a> a<br>link.</p>'
        result = safe_html(text)
        eq_(result, text)

    def test_disallowed_html(self):
        text = '<script>alert("xss")</script>'
        result = safe_html(text)
        eq_(result, text.replace('<', '&lt;').replace('>', '&gt;'))

    def test_mixed(self):
        text = '<p><script>alert("xss")</script></p>'
        result = safe_html(text)
        eq_(
            result,
            text
            .replace('<script>', '&lt;script&gt;')
            .replace('</script>', '&lt;/script&gt;')
        )


class TestMakeAbsolute(DjangoTestCase):

    def test_make_absolute(self):
        context = {}
        context['request'] = RequestFactory().get('/')

        result = make_absolute(context, reverse('main:home'))
        eq_(result, 'http://testserver/')

        result = make_absolute(context, result)
        eq_(result, 'http://testserver/')

        result = make_absolute(context, '//some.cdn.com/foo.js')
        eq_(result, 'http://some.cdn.com/foo.js')

        context['request'].is_secure = lambda: True
        result = make_absolute(context, '//some.cdn.com/foo.js')
        eq_(result, 'https://some.cdn.com/foo.js')
