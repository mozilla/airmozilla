import mock
from nose.tools import ok_, eq_

from django.conf import settings

from airmozilla.base.tests.testbase import DjangoTestCase, Response
from airmozilla.base import rev


class TestRev(DjangoTestCase):

    @mock.patch('requests.get')
    def test_get_orders(self, rget):
        def mocked_get(url, headers):
            ok_(settings.REV_BASE_URL in url)
            ok_(settings.REV_CLIENT_API_KEY in headers['Authorization'])
            ok_(settings.REV_USER_API_KEY in headers['Authorization'])
            return Response({
                'orders': [
                    {
                        'attachments': [],
                        'caption': {
                            'total_length': 1,
                            'total_length_seconds': 60
                        },
                        'comments': [],
                        'non_standard_tat_guarantee': False,
                        'order_number': 'CP0957651330',
                        'price': 1.0,
                        'priority': 'Normal',
                        'status': 'Complete'
                    }
                ],
                'page': 0,
                'results_per_page': 25,
                'total_count': 1
            })
        rget.side_effect = mocked_get

        orders = rev.get_orders()
        ok_(orders['orders'])
        ok_(orders['total_count'], 1)

    @mock.patch('requests.post')
    def test_input_order(self, rpost):

        def mocked_post(url, json, headers):
            ok_(settings.REV_BASE_URL in url)
            eq_(json['url'], 'https://example.com/file.MP4')
            eq_(json['content_type'], 'video/mpeg')
            eq_(json['filename'], 'file.MP4')
            ok_(settings.REV_CLIENT_API_KEY in headers['Authorization'])
            ok_(settings.REV_USER_API_KEY in headers['Authorization'])
            return Response('', status_code=201, headers={
                'Location': 'urn:rev:inputmedia:P3VwbG9hZHMvMjAxNi0xMC0yM',
            })

        rpost.side_effect = mocked_post

        result = rev.input_order('https://example.com/file.MP4')
        eq_(result, 'urn:rev:inputmedia:P3VwbG9hZHMvMjAxNi0xMC0yM')

    @mock.patch('requests.post')
    def test_place_order(self, rpost):

        def mocked_post(url, json, headers):
            ok_(settings.REV_BASE_URL in url)
            eq_(json['notification']['url'], 'https://example.com/callback')
            eq_(json['notification']['level'], 'FinalOnly')
            eq_(
                json['caption_options']['inputs'][0]['uri'],
                'urn:rev:inputmedia:P3VwbG9hZHMvMjAxNi0xMC0yM'
            )
            eq_(
                json['caption_options']['output_file_formats'],
                ['DFXP']
            )
            ok_(settings.REV_CLIENT_API_KEY in headers['Authorization'])
            ok_(settings.REV_USER_API_KEY in headers['Authorization'])
            return Response('', status_code=201, headers={
                'Location': settings.REV_BASE_URL + '/api/v1/orders/CP000001',
            })

        rpost.side_effect = mocked_post

        result = rev.place_order(
            'urn:rev:inputmedia:P3VwbG9hZHMvMjAxNi0xMC0yM',
            webhook_url='https://example.com/callback',
        )
        eq_(result, settings.REV_BASE_URL + '/api/v1/orders/CP000001')

    @mock.patch('requests.get')
    def test_get_order(self, rget):
        def mocked_get(url, headers):
            ok_(settings.REV_BASE_URL in url)
            ok_(settings.REV_CLIENT_API_KEY in headers['Authorization'])
            ok_(settings.REV_USER_API_KEY in headers['Authorization'])
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

        order = rev.get_order(
            settings.REV_BASE_URL + '/api/v1/orders/CP000001'
        )
        eq_(order['status'], 'Complete')
        eq_(order['order_number'], 'CP000001')

    @mock.patch('requests.post')
    def test_cancel_order(self, rpost):

        def mocked_post(url, headers):
            ok_(settings.REV_BASE_URL in url)
            ok_(settings.REV_CLIENT_API_KEY in headers['Authorization'])
            ok_(settings.REV_USER_API_KEY in headers['Authorization'])
            return Response(True, status_code=204)

        rpost.side_effect = mocked_post

        result = rev.cancel_order('CP000001')
        eq_(result, True)

    @mock.patch('requests.get')
    def test_get_attachment(self, rget):
        sample_captions = u"""
            1
            00:00:00,000 --> 00:00:10,500
            Rebecca: This is a sample first line with a speaker

            2
            0:00:10,500 --> 00:00:20,761
            ^and this is the second line with the same speaker,
        """.strip()

        def mocked_get(url, headers):
            ok_(settings.REV_BASE_URL in url)
            ok_(settings.REV_CLIENT_API_KEY in headers['Authorization'])
            ok_(settings.REV_USER_API_KEY in headers['Authorization'])
            return Response(sample_captions, headers={
                'Content-Disposition': 'attachment; filename=sample.srt',
                'Content-Type': 'text/x-rev-caption',
            })

        rget.side_effect = mocked_get
        result = rev.get_attachment('fyKpNl7bAgAAAAAA')
        eq_(result.text, sample_captions)
