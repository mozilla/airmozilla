import os

from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse
from django.core.files import File

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.main.models import Event
from airmozilla.closedcaptions.models import ClosedCaptions

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
