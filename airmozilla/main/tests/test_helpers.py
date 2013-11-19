import uuid
import shutil
import os
import mock
from nose.tools import eq_
from django.test import TestCase
from django.conf import settings
from django.db.utils import IntegrityError
from airmozilla.main.helpers import thumbnail, get_thumbnail, pluralize


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
