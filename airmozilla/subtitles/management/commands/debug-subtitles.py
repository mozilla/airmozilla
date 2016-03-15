import json
from pprint import pprint
from urlparse import urlparse

import requests

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from airmozilla.main.models import Event
from airmozilla.subtitles.models import AmaraVideo


class Command(BaseCommand):  # pragma: no cover

    def add_arguments(self, parser):
        parser.add_argument('slug-or-url-or-id', nargs='+')
        parser.add_argument(
            '--post',
            action='store_true',
            dest='post',
            default=False,
            help='Upload/Post video if not already there'
        )

    def handle(self, **options):
        identifiers = options['slug-or-url-or-id']
        if not identifiers:
            raise CommandError('slug-or-url-or-id')

        verbosity = int(options['verbosity'])
        verbose = verbosity > 1

        for arg in identifiers:
            if arg.isdigit():
                event = Event.objects.get(pk=arg)
            else:
                if '://' in arg:
                    slug = urlparse(arg).path.split('/')[1]
                else:
                    slug = arg
                event = Event.objects.get(slug=slug)
            if verbose:
                print repr(event)
            if not (
                event.template and 'vid.ly' in event.template.name.lower()
            ):
                raise NotImplementedError("Not a vid.ly archived event")
            video_url = self._get_webm_link(event)
            if verbose:
                print "\t", video_url
            result = self.find_video_by_url(video_url)

            if not result['objects'] and options['post']:
                if urlparse(video_url).netloc == 'vid.ly':
                    print "FROM", video_url
                    video_url = self.get_webm_actual_url(video_url)
                    print "TO", video_url
                post_result = self.post_video_by_url(
                    video_url,
                    title=event.title,
                    description=event.short_description or event.description,
                    duration=60
                )
                if verbose:
                    print post_result
                result = self.find_video_by_url(video_url)

            amara_video, __ = AmaraVideo.objects.get_or_create(
                event=event,
                video_url=video_url,
            )

            # Let's download the subtitles transript again
            transcript_before = amara_video.transcript
            transcript = self.download_subtitles(
                result['objects'][0]['id'],
                format='json'
            )
            if verbose:
                if transcript != transcript_before:
                    print "\tTranscript has changed",
                else:
                    print "\tTranscript has not changed"

            if verbose:
                pprint(transcript)
            amara_video.transcript = transcript
            amara_video.save()

    def _get_webm_link(self, event):
        tag = event.template_environment['tag']
        return 'https://vid.ly/%s?content=video&format=webm' % tag

    @property
    def headers(self):
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-api-username': settings.AMARA_API_USERNAME,
            'X-apikey': settings.AMARA_API_KEY
        }

    def find_video_by_url(self, video_url):
        url = settings.AMARA_BASE_URL + '/videos/'
        res = requests.get(url, headers=self.headers, params={
            'video_url': video_url
        })
        assert res.status_code == 200, res.status_code
        return res.json()

    def post_video_by_url(self, video_url, **kwargs):
        url = settings.AMARA_BASE_URL + '/videos/'
        params = dict(
            kwargs,
            video_url=video_url,
            team='mozilla'
        )
        res = requests.post(url, headers=self.headers, data=json.dumps(params))
        assert res.status_code == 200, res.status_code
        return res.json()

    def get_webm_actual_url(self, url):
        headers = {'Accept': 'video/webm'}
        res = requests.head(url, headers=headers)
        return res.headers['Location']

    def download_subtitles(self, video_id, format='json'):
        url = settings.AMARA_BASE_URL + (
            '/videos/%s/languages/en/subtitles/' % video_id
        )
        res = requests.get(url, headers=self.headers, params={
            'format': format
        })
        assert res.status_code == 200, res.status_code
        return res.json()
