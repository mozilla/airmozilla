import os
from cStringIO import StringIO

import mock
from nose.tools import eq_, ok_

from django.conf import settings
from django.core.files import File
from django.core.urlresolvers import reverse
from django.utils import timezone

from airmozilla.main.models import Event, VidlySubmission, Template
from airmozilla.closedcaptions.models import (
    ClosedCaptions,
    ClosedCaptionsTranscript,
    RevInput,
    RevOrder,
)
from airmozilla.base.tests.testbase import Response
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

    @mock.patch('requests.get')
    def test_event_rev_orders(self, rget):
        event = Event.objects.get(title='Test event')
        url = reverse('manage:event_rev_orders', args=(event.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('No Rev.com orders yet.' in response.content)

        rev_order = RevOrder.objects.create(
            event=event,
            order_number='CP000001',
            uri='https://example.com/api/orders/CP000001',
            input=RevInput.objects.create(
                url='https://example.com/file.mp4',
                content_type='video/mpeg',
                filename='file.mp4',
            ),
            output_file_formats=['DFXP'],
            created_user=self.user,
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('No Rev.com orders yet.' not in response.content)
        ok_(rev_order.input.url in response.content)
        ok_('DFXP' in response.content)
        ok_(self.user.email in response.content)
        ok_(rev_order.order_number in response.content)

        def mocked_get(url, headers):
            return Response({
                'attachments': [{
                    'id': 'fyKpNl7bAgAAAAAA',
                    'kind': 'caption',
                    'links': [{
                        'content-type': 'text/x-rev-caption',
                        'href': (
                            'https://example.com/api/v1/attachments/'
                            'fyKpNl7bAgAAAAAA/content'
                            ),
                        'rel': 'content'
                    }],
                    'name': 'sample_caption.srt',
                }],
                'caption': {
                    'total_length': 1,
                    'total_length_seconds': 60
                },
                'comments': [],
                'non_standard_tat_guarantee': False,
                'order_number': 'CP000001',
                'price': 1.0,
                'priority': 'Normal',
                'status': 'Complete'
            })
        rget.side_effect = mocked_get

        rev_order.update_status()
        ok_(rev_order.status, 'Complete')

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Complete' in response.content)

    @mock.patch('requests.post')
    @mock.patch('requests.get')
    def test_new_event_rev_order(self, rget, rpost):
        event = Event.objects.get(title='Test event')
        url = reverse('manage:new_event_rev_order', args=(event.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        response = self.client.post(url, {})
        eq_(response.status_code, 200)
        ok_('This field is required' in response.content)

        def mocked_post(url, json, headers):
            if url.endswith('/inputs'):
                return Response('', status_code=201, headers={
                    'Location': 'urn:rev:inputmedia:P3VwbG9hZHMvMjAxNi0xMC0yM',
                })
            elif url.endswith('/orders'):
                return Response('', status_code=201, headers={
                    'Location': (
                        settings.REV_BASE_URL + '/api/v1/orders/CP000001'
                    ),
                })
            raise NotImplementedError(url)

        rpost.side_effect = mocked_post

        def mocked_get(url, headers):
            return Response({
                'attachments': [{
                    'id': 'fyKpNl7bAgAAAAAA',
                    'kind': 'caption',
                    'links': [{
                        'content-type': 'text/x-rev-caption',
                        'href': (
                            'https://example.com/api/v1/attachments/'
                            'fyKpNl7bAgAAAAAA/content'
                            ),
                        'rel': 'content'
                    }],
                    'name': 'sample_caption.srt',
                }],
                'caption': {
                    'total_length': 1,
                    'total_length_seconds': 60
                },
                'comments': [],
                'non_standard_tat_guarantee': False,
                'order_number': 'CP000001',
                'price': 1.0,
                'priority': 'Normal',
                'status': 'Complete'
            })

        rget.side_effect = mocked_get

        response = self.client.post(url, {
            'url': 'https://example.com/file.mp4',
            'content_type': 'video/mpeg',
            'filename': 'file.mp4',
            'output_file_formats': ['Dfxp'],
        })
        eq_(response.status_code, 302)
        ok_(RevOrder.objects.filter(event=event))

    @mock.patch('requests.head')
    def test_new_event_rev_order_vidly_prefilled(self, rhead):
        event = Event.objects.get(title='Test event')
        event.template = Template.objects.create(
            name='Vid.ly'
        )
        event.template_environment = {'tag': 'abc123'}
        event.save()
        VidlySubmission.objects.create(
            event=event,
            tag='abc123',
            url='https://s3.example.com/file.webm',
            finished=timezone.now(),
        )

        def mocked_head(url):
            return Response('', status_code=302, headers={
                'Location': 'https://cloudfront.example.com/file.mp4'
            })

        rhead.side_effect = mocked_head

        url = reverse('manage:new_event_rev_order', args=(event.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('https://s3.example.com/file.webm' not in response.content)
        ok_('https://cloudfront.example.com/file.mp4' in response.content)

    @mock.patch('requests.post')
    def test_event_rev_orders_cancel(self, rpost):
        event = Event.objects.get(title='Test event')

        rev_order = RevOrder.objects.create(
            event=event,
            order_number='CP000001',
            uri='https://example.com/api/orders/CP000001',
            input=RevInput.objects.create(
                url='https://example.com/file.mp4',
                content_type='video/mpeg',
                filename='file.mp4',
            ),
            output_file_formats=['DFXP'],
            created_user=self.user,
        )
        assert not rev_order.cancelled

        def mocked_post(url, headers):
            assert 'CP000001' in url
            return Response(True, status_code=204)

        rpost.side_effect = mocked_post

        url = reverse(
            'manage:event_rev_orders_cancel',
            args=(event.id, rev_order.id)
        )
        response = self.client.get(url)
        eq_(response.status_code, 405)
        response = self.client.post(url)
        eq_(response.status_code, 302)

        rev_order = RevOrder.objects.get(id=rev_order.id)
        ok_(rev_order.cancelled)

    @mock.patch('requests.get')
    def test_event_rev_orders_update(self, rget):

        def mocked_get(url, headers):
            assert 'CP000001' in url
            return Response({
                'attachments': [{
                    'id': 'fyKpNl7bAgAAAAAA',
                    'kind': 'caption',
                    'links': [{
                        'content-type': 'text/x-rev-caption',
                        'href': (
                            'https://example.com/api/v1/attachments/'
                            'fyKpNl7bAgAAAAAA/content'
                            ),
                        'rel': 'content'
                    }],
                    'name': 'sample_caption.srt',
                }],
                'caption': {
                    'total_length': 1,
                    'total_length_seconds': 60
                },
                'comments': [],
                'non_standard_tat_guarantee': False,
                'order_number': 'CP000001',
                'price': 1.0,
                'priority': 'Normal',
                'status': 'Complete'
            })

        rget.side_effect = mocked_get

        event = Event.objects.get(title='Test event')

        rev_order = RevOrder.objects.create(
            event=event,
            order_number='CP000001',
            uri='https://example.com/api/orders/CP000001',
            input=RevInput.objects.create(
                url='https://example.com/file.mp4',
                content_type='video/mpeg',
                filename='file.mp4',
            ),
            output_file_formats=['DFXP'],
            created_user=self.user,
        )
        assert not rev_order.status

        url = reverse(
            'manage:event_rev_orders_update',
            args=(event.id, rev_order.id)
        )
        response = self.client.get(url)
        eq_(response.status_code, 405)
        response = self.client.post(url)
        eq_(response.status_code, 302)

        rev_order = RevOrder.objects.get(id=rev_order.id)

    @mock.patch('requests.get')
    def test_event_rev_orders_download(self, rget):
        sample_captions = (
            '1\n00:00:00 - 00:00:00,000 --> 00:00:10,500\n'
            'Rebecca: This is a sample first line with a speaker'
        )

        def mocked_get(url, headers):
            if 'fyKpNl7bAgAAAAAA' in url and url.endswith('/content'):
                return Response(
                    sample_captions,
                    headers={
                        'Content-Disposition': (
                            'attachment; filename=sample.srt'
                        ),
                        'Content-Type': 'text/x-rev-caption',
                    }
                )

            assert 'CP000001' in url
            return Response({
                'attachments': [{
                    'id': 'fyKpNl7bAgAAAAAA',
                    'kind': 'caption',
                    'links': [{
                        'content-type': 'text/x-rev-caption',
                        'href': (
                            'https://example.com/api/v1/attachments/'
                            'fyKpNl7bAgAAAAAA/content'
                            ),
                        'rel': 'content'
                    }],
                    'name': 'sample_caption.srt',
                }],
                'caption': {
                    'total_length': 1,
                    'total_length_seconds': 60
                },
                'comments': [],
                'non_standard_tat_guarantee': False,
                'order_number': 'CP000001',
                'price': 1.0,
                'priority': 'Normal',
                'status': 'Complete'
            })

        rget.side_effect = mocked_get

        event = Event.objects.get(title='Test event')

        rev_order = RevOrder.objects.create(
            event=event,
            order_number='CP000001',
            uri='https://example.com/api/orders/CP000001',
            input=RevInput.objects.create(
                url='https://example.com/file.mp4',
                content_type='video/mpeg',
                filename='file.mp4',
            ),
            output_file_formats=['DFXP'],
            created_user=self.user,
        )
        assert not rev_order.status

        url = reverse(
            'manage:event_rev_orders_download',
            args=(event.id, rev_order.id, 'junk')
        )
        response = self.client.get(url)
        eq_(response.status_code, 400)

        url = reverse(
            'manage:event_rev_orders_download',
            args=(event.id, rev_order.id, 'fyKpNl7bAgAAAAAA')
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response.content, sample_captions)
        eq_(response['Content-Type'], 'text/x-rev-caption')
        eq_(response['Content-Disposition'], 'attachment; filename=sample.srt')
