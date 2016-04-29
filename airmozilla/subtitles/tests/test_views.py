from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse

from airmozilla.main.models import Event
from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.subtitles.models import AmaraVideo, AmaraCallback


class TestViews(DjangoTestCase):

    def test_amara_callback_successful(self):
        url = reverse('subtitles:amara_callback')
        event = Event.objects.get(title='Test event')
        amara_video = AmaraVideo.objects.create(
            event=event,
            video_id='abc123',
            video_url='http://example.com/foo.mp4',
        )

        response = self.post_json(url, {
            'event': 'new-language',
            'video_id': amara_video.video_id,
            'api_url': 'http://example.com/api/url',
            'team': 'myteam',
            'project': 'myproject',
            'language_code': 'sv',
        })
        eq_(response.status_code, 200)

        amara_callback = AmaraCallback.objects.get(
            api_url='http://example.com/api/url'
        )
        eq_(amara_callback.amara_video, amara_video)
        ok_(amara_callback.payload)
        eq_(amara_callback.api_url, 'http://example.com/api/url')
        eq_(amara_callback.team, 'myteam')
        eq_(amara_callback.project, 'myproject')
        eq_(amara_callback.language_code, 'sv')

    def test_amara_callback_variants(self):
        url = reverse('subtitles:amara_callback')
        response = self.client.get(url)
        eq_(response.status_code, 405)

        response = self.client.post(url)
        eq_(response.status_code, 400)

        response = self.post_json(url)
        eq_(response.status_code, 400)

        response = self.post_json(url, {
            'no': 'video_id',
            'api_url': 'http://example.com/api/url',
        })
        eq_(response.status_code, 400)
        response = self.post_json(url, {
            'video_id': 'xxxyyyzzz',
            'no': 'api_url',
        })
        eq_(response.status_code, 400)

        response = self.post_json(url, {
            'video_id': 'xxxyyyzzz',
            'api_url': 'http://example.com/api/url',
        })
        eq_(response.status_code, 200)
