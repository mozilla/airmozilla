import mock
from nose.tools import ok_, eq_, assert_raises

from django.core.files import File
from django.conf import settings

from airmozilla.main.models import Event, Picture, Template
from airmozilla.base.tests.testbase import DjangoTestCase, Response
from airmozilla.base import amara


class TestAmara(DjangoTestCase):

    @mock.patch('requests.get')
    def test_get_videos(self, rget):

        def mocked_get(url, params, headers):

            ok_(headers['X-api-key'], settings.AMARA_API_KEY)
            ok_(headers['X-api-username'], settings.AMARA_USERNAME)
            ok_(params['project'], settings.AMARA_PROJECT)
            ok_(params['team'], settings.AMARA_TEAM)

            return Response({
                'meta': {
                    'limit': 20,
                    'next': None,
                    'offset': 0,
                    'previous': None,
                    'total_count': 1
                },
                'objects': [
                    {
                        'all_urls': [
                            'https://example.com/p3s3q8/hd_mp4.mp4'
                        ],
                        'created': '2016-04-29T14:23:21Z',
                        'description': 'My Description',
                        'duration': 127,
                        'id': 'XDvDyhpThz3A',
                        'languages': [],
                        'metadata': {},
                        'original_language': None,
                        'primary_audio_language_code': None,
                        'project': 'airmozilla',
                        'resource_uri': 'https://example.com/api/videos/XD/',
                        'subtitle_languages_uri': 'https://.../languages/',
                        'team': 'mozilla',
                        'thumbnail': 'https://...cdfd806e64630358.jpg',
                        'title': 'Stuff Mozillians Say',
                        'urls_uri': 'https://...hpThz3A/urls/',
                        'video_type': 'H'
                    }
                ]}
            )

        rget.side_effect = mocked_get

        videos = amara.get_videos()
        ok_(videos['objects'][0])
        eq_(videos['objects'][0]['description'], 'My Description')

    @mock.patch('requests.post')
    def test_upload_video(self, rpost):
        event = Event.objects.get(title='Test event')
        with open(self.main_image) as fp:
            Picture.objects.create(
                file=File(fp),
                notes='Some notes',
                event=event
            )

        event.template = Template.objects.create(name='YouTube')
        event.template_environment = {'id': 'abc123'}
        event.duration = 3600
        event.save()

        def mocked_post(url, data, headers):
            eq_(data['description'], event.description)
            eq_(data['title'], event.title)
            eq_(data['duration'], 3600)
            eq_(data['team'], settings.AMARA_TEAM)
            eq_(data['project'], settings.AMARA_PROJECT)
            eq_(data['video_url'], 'https://www.youtube.com/watch?v=abc123')
            ok_(data['thumbnail'])
            return Response({
                'id': '123-aaa-bbb',
                'other': 'stuff',
            }, status_code=201)

        rpost.side_effect = mocked_post

        amara_video = amara.upload_video(event)
        eq_(amara_video.video_id, '123-aaa-bbb')
        eq_(amara_video.video_url, 'https://www.youtube.com/watch?v=abc123')
        eq_(amara_video.event, event)
        eq_(amara_video.upload_info['other'], 'stuff')

    @mock.patch('requests.post')
    def test_upload_video_fail(self, rpost):
        event = Event.objects.get(title='Test event')
        with open(self.main_image) as fp:
            Picture.objects.create(
                file=File(fp),
                notes='Some notes',
                event=event
            )

        event.template = Template.objects.create(name='YouTube')
        event.template_environment = {'id': 'abc123'}
        event.duration = 3600
        event.save()

        def mocked_post(url, data, headers):
            return Response('Something Wrong', 500)

        rpost.side_effect = mocked_post

        assert_raises(amara.UploadError, amara.upload_video, event)
