import os
import shutil
import tempfile

import mock
from nose.tools import ok_

from django.conf import settings
from django.core.cache import cache

from airmozilla.base.tests.testbase import DjangoTestCase, Response
from airmozilla.main.models import Chapter, Event, Template
from airmozilla.chapters import images


class TestImages(DjangoTestCase):
    sample_jpg = 'airmozilla/manage/tests/presenting.jpg'

    _original_temp_directory_name = settings.SCREENCAPTURES_TEMP_DIRECTORY_NAME

    def setUp(self):
        super(TestImages, self).setUp()
        settings.SCREENCAPTURES_TEMP_DIRECTORY_NAME = (
            'test_' + self._original_temp_directory_name
        )

    def tearDown(self):
        cache.clear()
        assert settings.SCREENCAPTURES_TEMP_DIRECTORY_NAME.startswith('test_')
        temp_dir = os.path.join(
            tempfile.gettempdir(),
            settings.SCREENCAPTURES_TEMP_DIRECTORY_NAME
        )
        if os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir)
        super(TestImages, self).tearDown()

    @mock.patch('airmozilla.manage.vidly.logging')
    @mock.patch('requests.head')
    @mock.patch('subprocess.Popen')
    def test_create_missing_chapterimages(
        self,
        mock_popen,
        rhead,
        p_logging
    ):

        def mocked_head(url, **options):
            return Response(
                '',
                200
            )

        rhead.side_effect = mocked_head

        ffmpeged_urls = []

        sample_jpg = self.sample_jpg

        def mocked_popen(command, **kwargs):
            url = command[4]
            ffmpeged_urls.append(url)
            destination = command[-1]
            assert os.path.isdir(os.path.dirname(destination))

            class Inner:
                def communicate(self):
                    out = err = ''
                    if 'xyz123' in url:
                        # 04.jpg because the chapter is at timestamp 4 seconds
                        if '04.jpg' in destination:
                            shutil.copyfile(sample_jpg, destination)
                        else:
                            raise NotImplementedError(destination)
                    else:
                        raise NotImplementedError(url)
                    return out, err

            return Inner()

        mock_popen.side_effect = mocked_popen

        event = Event.objects.get(title='Test event')

        # Nothing will happen because the event doesn't have a duration or
        # Vid.ly template.
        images.create_missing_chapterimages()

        event.duration = 100
        template = Template.objects.create(
            name='Vid.ly Something',
            content="{{ tag }}"
        )
        event.template = template
        event.template_environment = {'tag': 'xyz123'}
        event.save()

        # Still nothing will happen because the event doesn't have any
        # chapters.
        images.create_missing_chapterimages()

        chapter = Chapter.objects.create(
            event=event,
            timestamp=4,
            text='Right Here',
            user=event.creator,
        )

        images.create_missing_chapterimages()
        ok_(Chapter.objects.get(id=chapter.id).image)
        assert ffmpeged_urls
