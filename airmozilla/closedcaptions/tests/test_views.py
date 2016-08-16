import os

from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse
from django.core.files import File

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.main.models import Event, Template
from airmozilla.closedcaptions.models import (
    ClosedCaptions,
    ClosedCaptionsTranscript,
)

TEST_DIRECTORY = os.path.dirname(__file__)


class TestClosedCaptions(DjangoTestCase):

    def setUp(self):
        super(TestClosedCaptions, self).setUp()
        self.event = Event.objects.get(title='Test event')

    def test_download_not_found(self):
        filepath = os.path.join(TEST_DIRECTORY, 'example.srt')
        with open(filepath) as f:
            item = ClosedCaptions.objects.create(
                event=self.event,
                file=File(f),
            )
        url = reverse('closedcaptions:download', args=(
            item.filename_hash[::-1],
            item.id,
            self.event.slug,
            'txt'
        ))
        response = self.client.get(url)
        eq_(response.status_code, 404)

        url = reverse('closedcaptions:download', args=(
            item.filename_hash,
            item.id,
            'junk-slug',
            'txt'
        ))
        response = self.client.get(url)
        eq_(response.status_code, 404)

        url = reverse('closedcaptions:download', args=(
            item.filename_hash,
            989999,
            self.event.slug,
            'txt'
        ))
        response = self.client.get(url)
        eq_(response.status_code, 404)

        url = reverse('closedcaptions:download', args=(
            item.filename_hash,
            item.id,
            self.event.slug,
            'xxx'
        ))
        response = self.client.get(url)
        eq_(response.status_code, 404)

    def test_download_from_srt(self):
        filepath = os.path.join(TEST_DIRECTORY, 'example.srt')
        with open(filepath) as f:
            item = ClosedCaptions.objects.create(
                event=self.event,
                file=File(f),
            )

        # txt
        url = reverse('closedcaptions:download', args=(
            item.filename_hash,
            item.id,
            self.event.slug,
            'txt'
        ))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'text/plain')
        ok_(response.content.startswith('Language: en-US\n'))

        # dfxp
        url = reverse('closedcaptions:download', args=(
            item.filename_hash,
            item.id,
            self.event.slug,
            'dfxp'
        ))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'application/ttml+xml; charset=utf-8')
        ok_(response.content.startswith(
            '<?xml version="1.0" encoding="utf-8"?>\n<tt'
        ))

        # srt
        url = reverse('closedcaptions:download', args=(
            item.filename_hash,
            item.id,
            self.event.slug,
            'srt'
        ))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'text/plain')
        ok_(response.content.startswith(
            '1\n00:00:09,209 -->'
        ))

        # vtt
        url = reverse('closedcaptions:download', args=(
            item.filename_hash,
            item.id,
            self.event.slug,
            'vtt'
        ))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'text/vtt')
        ok_(response.content.startswith(
            'WEBVTT\n\n00:09.209 -->'
        ))

    def test_download_from_dfxp(self):
        filepath = os.path.join(TEST_DIRECTORY, 'example.dfxp')
        with open(filepath) as f:
            item = ClosedCaptions.objects.create(
                event=self.event,
                file=File(f),
            )

        # txt
        url = reverse('closedcaptions:download', args=(
            item.filename_hash,
            item.id,
            self.event.slug,
            'txt'
        ))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'text/plain')
        ok_(response.content.startswith('Language: en-US\n'))

        # dfxp
        url = reverse('closedcaptions:download', args=(
            item.filename_hash,
            item.id,
            self.event.slug,
            'dfxp'
        ))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'application/ttml+xml; charset=utf-8')
        ok_(response.content.startswith(
            '<?xml version="1.0" encoding="utf-8"?>\n<tt'
        ))

        # srt
        url = reverse('closedcaptions:download', args=(
            item.filename_hash,
            item.id,
            self.event.slug,
            'srt'
        ))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'text/plain')
        ok_(response.content.startswith(
            '1\n00:00:00,983 -->'
        ))

        # vtt
        url = reverse('closedcaptions:download', args=(
            item.filename_hash,
            item.id,
            self.event.slug,
            'vtt'
        ))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'text/vtt')
        ok_(response.content.startswith(
            'WEBVTT\n\n00:00.983 -->'
        ))

    def test_view_event_with_transcript(self):
        filepath = os.path.join(TEST_DIRECTORY, 'example.dfxp')
        with open(filepath) as f:
            item = ClosedCaptions.objects.create(
                event=self.event,
                file=File(f),
            )
        item.set_transcript_from_file()
        item.save()

        # The transcript download is on the Download tab which
        # only works if you have a Vid.ly video
        self.event.template = Template.objects.create(
            name='Vid.ly',
            content='<iframe>{{tag}}</iframe>',
        )
        self.event.template_environment = {'tag': 'abc123'}
        self.event.save()

        assert self.event.privacy == Event.PRIVACY_PUBLIC

        url = reverse('main:event', args=(self.event.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        download_url = reverse('closedcaptions:download', args=(
            item.filename_hash,
            item.id,
            self.event.slug,
            'txt'
        ))
        # It's not there because the closed captions hasn't
        # been associated with the event yet.
        ok_('Transcript:' not in response.content)
        ok_(download_url not in response.content)

        ClosedCaptionsTranscript.objects.create(
            event=self.event,
            closedcaptions=item,
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Transcript:' in response.content)
        ok_(download_url in response.content)
