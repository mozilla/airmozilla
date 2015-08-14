from cStringIO import StringIO
import mock
from mock import Mock

from nose.tools import eq_, ok_

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.main.models import Event, VidlySubmission
from airmozilla.manage.tests.views.test_vidlymedia import (
    SAMPLE_MEDIA_SUBMITTED_XML,
)
from airmozilla.popcorn.renderer import render_edit
from airmozilla.popcorn.models import PopcornEdit


class TestPopcornRender(DjangoTestCase):

    @mock.patch('airmozilla.manage.vidly.urllib2')
    @mock.patch('airmozilla.popcorn.renderer.Key')
    @mock.patch('boto.connect_s3')
    @mock.patch('airmozilla.popcorn.renderer.process_json')
    def test_render(self, p_process_json, p_connect_s3, p_key, p_urllib2):
        def make_mock_request(url, querystring):
            return mock.MagicMock()

        def mocked_urlopen(request):
            xml_string = SAMPLE_MEDIA_SUBMITTED_XML
            return StringIO(xml_string)

        def process_json_mock(data, out, background_color='#000000'):
            with open(out, 'w') as f:
                f.write('')

        def generate_key_mock():
            def mock_generate_url(expires_in=0, query_auth=False):
                return 'foo'

            key_mock = Mock()
            key_mock.generate_url.side_effect = mock_generate_url
            return key_mock

        def get_bucket_mock(name):
            m_bucket = Mock()
            m_bucket.name = name
            return m_bucket

        def make_mock_key(bucket):
            def set_contents_mock(filename):
                return

            def generate_url_mock(expires_in, query_auth):
                return 'https://example.com'

            mocked_key = Mock()
            mocked_key.set_contents_from_filename.side_effect = \
                set_contents_mock
            mocked_key.generate_url.side_effect = generate_url_mock
            return mocked_key

        p_key.side_effect = make_mock_key

        p_urllib2.Request.side_effect = make_mock_request
        p_urllib2.urlopen = mocked_urlopen

        p_process_json.side_effect = process_json_mock
        p_connect_s3().get_bucket.side_effect = get_bucket_mock
        p_key.side_effect = make_mock_key

        event = Event.objects.get(title='Test event')
        event.template.name = 'Vid.ly Template'
        event.template.save()

        VidlySubmission.objects.create(
            event=event,
            tag='abc123',
            url='http://s3.com/file.mpg',
            hd=True,
            token_protection=False
        )

        edit = PopcornEdit.objects.create(
            event=event,
            status=PopcornEdit.STATUS_PENDING,
            data={'background': '#000', 'data': {}},
            user=event.creator,
        )

        render_edit(edit.id)

        assert VidlySubmission.objects.filter(event=event).count() == 2
        vidly_submission, = (
            VidlySubmission.objects
            .filter(event=event)
            .order_by('-submission_time')[:1]
        )
        assert vidly_submission.tag != 'abc123'  # the original was 'abc123'

        edit = PopcornEdit.objects.get(id=edit.id)

        eq_(edit.status, PopcornEdit.STATUS_SUCCESS)
        ok_(vidly_submission)
