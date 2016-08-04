import os
from cStringIO import StringIO

import mock
from nose.tools import eq_, ok_

from django.core.files import File
from django.core.urlresolvers import reverse

from airmozilla.main.models import Event, VidlySubmission
from airmozilla.closedcaptions.models import (
    ClosedCaptions,
    ClosedCaptionsTranscript,
)
from .base import ManageTestCase
from airmozilla.closedcaptions.tests.test_views import TEST_DIRECTORY
from airmozilla.manage.tests.test_vidly import SAMPLE_MEDIA_UPDATED_XML


class TestClosedCaptions(ManageTestCase):

    def test_upload_closed_captions(self):
        event = Event.objects.get(title='Test event')
        url = reverse('manage:event_closed_captions', args=(event.id,))

        # let's upload all sample files we have
        filenames = ('example.dfxp', 'example.srt')
        for filename in filenames:
            with open(os.path.join(TEST_DIRECTORY, filename)) as fp:
                response = self.client.post(url, {'file': fp})
                eq_(response.status_code, 302)

        eq_(
            ClosedCaptions.objects.filter(event=event).count(),
            len(filenames)
        )

        # Render the page now that there's content in there
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # some incompatible file
        filepath = os.path.join(TEST_DIRECTORY, 'test_views.py')
        with open(filepath) as fp:
            response = self.client.post(url, {'file': fp})
            eq_(response.status_code, 200)
            ok_(
                'Not a valid caption file that could be recognized' in
                response.content
            )

        # lastly delete the example.srt one
        item, = [
            x for x in ClosedCaptions.objects.filter(event=event)
            if x.file_info['name'] == 'example.srt'
        ]
        url = reverse('manage:event_closed_captions_delete', args=(
            event.id,
            item.id,
        ))
        response = self.client.post(url)
        eq_(response.status_code, 302)
        eq_(
            ClosedCaptions.objects.filter(event=event).count(),
            len(filenames) - 1
        )

    @mock.patch('urllib2.urlopen')
    def test_upload_closed_captions_submit(self, p_urlopen):

        def mocked_urlopen(request):
            return StringIO(SAMPLE_MEDIA_UPDATED_XML.strip())

        p_urlopen.side_effect = mocked_urlopen

        event = Event.objects.get(title='Test event')
        event.duration = 120
        event.template_environment = {'tag': 'abc123'}
        event.save()
        VidlySubmission.objects.create(
            event=event,
            tag='abc123',
            url='https://s3.example.com/file.mov',
            hd=True,
        )

        with open(os.path.join(TEST_DIRECTORY, 'example.dfxp')) as fp:
            closedcaptions = ClosedCaptions.objects.create(
                event=event,
                file=File(fp),
            )

        url = reverse('manage:event_closed_captions_submit', args=(
            event.id,
            closedcaptions.id,
        ))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # let's submit it
        response = self.client.post(url, {'file_format': 'dfxp'})
        eq_(response.status_code, 302)

        # reload
        closedcaptions = ClosedCaptions.objects.get(id=closedcaptions.id)
        first, = closedcaptions.submission_info['submissions']
        eq_(first['url'], 'https://s3.example.com/file.mov')
        eq_(first['tag'], 'abc123')
        eq_(first['hd'], True)
        ok_(first['public_url'])

        response = self.client.get(url)
        eq_(response.status_code, 200)
        # expect the link to the closed captions download is there
        download_url = reverse('closedcaptions:download', args=(
            closedcaptions.filename_hash,
            closedcaptions.id,
            event.slug,
            'dfxp'
        ))
        ok_(download_url in response.content)

    def test_upload_closed_captions_transcript(self):
        event = Event.objects.get(title='Test event')

        with open(os.path.join(TEST_DIRECTORY, 'example.dfxp')) as fp:
            closedcaptions = ClosedCaptions.objects.create(
                event=event,
                file=File(fp),
            )

        url = reverse('manage:event_closed_captions_transcript', args=(
            event.id,
            closedcaptions.id,
        ))
        response = self.client.get(url)
        # Just rendering this checks the preview works
        eq_(response.status_code, 200)

        response = self.client.post(url)
        eq_(response.status_code, 302)

        ok_(ClosedCaptionsTranscript.objects.get(
            event=event,
            closedcaptions=closedcaptions
        ))
        event = Event.objects.get(id=event.id)
        ok_(event.transcript.startswith('Ping'))
