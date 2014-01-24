import uuid
import shutil
import os
import mock
from nose.tools import eq_
from django.test import TestCase
from django.conf import settings
from django.db.utils import IntegrityError
from airmozilla.main.helpers import (
    thumbnail,
    get_thumbnail,
    pluralize,
    short_desc,
    truncate_words
)


class TestThumbnailHelper(TestCase):

    def setUp(self):
        sample_file = os.path.join(
            os.path.dirname(__file__),
            'animage.png'
        )
        assert os.path.isfile(sample_file)

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

    @mock.patch('airmozilla.main.helpers.time')
    @mock.patch('airmozilla.main.helpers.get_thumbnail')
    def test_thumbnail_with_some_integrityerrors(self, mocked_get_thumbnail,
                                                 mocked_time):

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


class TestPluralizer(TestCase):

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


class TestTruncation(TestCase):

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
        eq_(result, 'Hacking with')

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
