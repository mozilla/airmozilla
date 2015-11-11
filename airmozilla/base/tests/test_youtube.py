import unittest

import mock
from nose.tools import eq_

from airmozilla.base import youtube
from airmozilla.base.tests.testbase import Response


class MiscTestCase(unittest.TestCase):

    def test_duration(self):
        value = 'PT30M13S'
        seconds = youtube.youtube_duration_to_seconds(value)
        eq_(seconds, 30 * 60 + 13)

        value = 'PT2H30M13S'
        seconds = youtube.youtube_duration_to_seconds(value)
        eq_(seconds, 2 * 60 * 60 + 30 * 60 + 13)

    @mock.patch('requests.get')
    def test_find_best_thumbnail_url(self, rget):

        def mocked_get(url):
            assert url.endswith('maxresdefault.jpg')
            return Response('', 404)

        rget.side_effect = mocked_get

        thumbnails = {
            'default': {
                'height': 90,
                'url': 'https://i.y00timg.com/vi/PiBfOFqDIAI/default.jpg',
                'width': 120
            },
            'high': {
                'height': 360,
                'url': 'https://i.y00timg.com/vi/PiBfOFqDIAI/hqdefault.jpg',
                'width': 480
            },
            'medium': {
                'height': 180,
                'url': 'https://i.y00timg.com/vi/PiBfOFqDIAI/mqdefault.jpg',
                'width': 320
            }
        }

        url = youtube.find_best_thumbnail_url(thumbnails)
        eq_(url, thumbnails['high']['url'])

    @mock.patch('requests.get')
    def test_find_best_thumbnail_url_sneaky(self, rget):

        def mocked_get(url):
            assert url.endswith('maxresdefault.jpg')
            return Response('some binary data')

        rget.side_effect = mocked_get

        thumbnails = {
            'default': {
                'height': 90,
                'url': 'https://i.y00timg.com/vi/PiBfOFqDIAI/default.jpg',
                'width': 120
            },
            'high': {
                'height': 360,
                'url': 'https://i.y00timg.com/vi/PiBfOFqDIAI/hqdefault.jpg',
                'width': 480
            },
            'medium': {
                'height': 180,
                'url': 'https://i.y00timg.com/vi/PiBfOFqDIAI/mqdefault.jpg',
                'width': 320
            }
        }

        url = youtube.find_best_thumbnail_url(thumbnails)
        eq_(url, thumbnails['high']['url'].replace(
            'hqdefault.jpg',
            'maxresdefault.jpg'
        ))
