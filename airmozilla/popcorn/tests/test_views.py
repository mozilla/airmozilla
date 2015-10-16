import datetime
import json
from cStringIO import StringIO

import mock
from nose.tools import eq_, ok_
import xmltodict

from django.core import mail
from django.test.utils import override_settings
from django.utils import timezone
from django.core.urlresolvers import reverse

from airmozilla.base.tests.testbase import DjangoTestCase, Response
from airmozilla.main.models import Event, VidlySubmission, Template
from airmozilla.uploads.models import Upload
from airmozilla.manage.tests.views.test_vidlymedia import (
    get_custom_XML,
    SAMPLE_MEDIA_RESULT_SUCCESS,
    SAMPLE_MEDIA_RESULT_FAILED,
)
from airmozilla.popcorn.models import PopcornEdit


class TestPopcornEvent(DjangoTestCase):

    def setUp(self):
        super(TestPopcornEvent, self).setUp()

        # The event we're going to clone needs to have a real image
        # associated with it so it can be rendered.
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)

    @mock.patch('requests.head')
    def test_meta_data_api(self, rhead):
        location = 'http://localhost'

        def mocked_head(url, **options):
            return Response(
                '',
                302,
                headers={
                    'location': location
                }
            )

        rhead.side_effect = mocked_head

        event = Event.objects.get(title='Test event')
        url = reverse('popcorn:event_meta_data')

        response = self.client.get(url, {})
        eq_(response.status_code, 400)
        event.template.name = 'this is a vid.ly video'
        event.template.save()

        event.template_environment = {'tag': 'abc123'}
        event.save()

        response = self.client.get(url, {'slug': event.slug})
        content = json.loads(response.content)

        eq_(response.status_code, 200)
        ok_(content['preview_img'])
        eq_(content['description'], 'sadfasdf')
        eq_(content['title'], event.title)
        eq_(content['video_url'], location)
        eq_(response['Access-Control-Allow-Origin'], '*')

    @mock.patch('requests.head')
    def test_popcorn_data(self, rhead):
        location = 'http://localhost'

        def mocked_head(url, **options):
            return Response(
                '',
                302,
                headers={
                    'location': location
                }
            )

        rhead.side_effect = mocked_head

        event = Event.objects.get(title='Test event')
        event.template.name = 'this is a vid.ly video'
        event.template.save()

        event.template_environment = {'tag': 'abc123'}
        event.save()

        url = reverse('popcorn:popcorn_data')

        response = self.client.get(url, {'slug': event.slug})
        # because we're not logged in
        eq_(response.status_code, 302), rhead

        self._login()

        response = self.client.get(url)
        # because there is no slug
        eq_(response.status_code, 400)

        response = self.client.get(url, {'slug': event.slug})
        eq_(response.status_code, 200)

        content = json.loads(response.content)

        ok_(content['metadata'])

    def test_popcorn_data_exists(self):
        event = Event.objects.get(title='Test event')
        event.template.name = 'this is a vid.ly video'
        event.template.save()

        event.template_environment = {'tag': 'abc123'}
        event.save()

        edit = PopcornEdit.objects.create(
            event=event,
            data={'foo': 'bar'},
            status=PopcornEdit.STATUS_SUCCESS
        )

        url = reverse('popcorn:popcorn_data')

        self._login()

        response = self.client.get(url, {'slug': event.slug})
        eq_(response.status_code, 200)

        content = json.loads(response.content)

        eq_(content['data'], edit.data)

    def test_popcorn_editor(self):
        event = Event.objects.get(title='Test event')
        event.template.name = 'this is a vid.ly video'
        event.template.save()

        event.template_environment = {'tag': 'abc123'}
        event.save()

        url = reverse('popcorn:render_editor', args=(event.slug,))

        response = self.client.get(url, {'slug': event.slug})
        eq_(response.status_code, 302)

        event.privacy = Event.PRIVACY_COMPANY
        event.save()

        response = self.client.get(url, {'slug': event.slug})
        eq_(response.status_code, 302)

        self._login()

        response = self.client.get(url, {'slug': event.slug})
        eq_(response.status_code, 200)

    def test_save_edit(self):
        event = Event.objects.get(title='Test event')
        event.template.name = 'this is a vid.ly video'
        event.template.save()

        event.template_environment = {'tag': 'abc123'}
        event.save()

        url = reverse('popcorn:save_edit')

        self._login()

        response = self.client.post(url, {
            'slug': event.slug,
        })
        # Should error due to missing data field
        eq_(response.status_code, 400)

        response = self.client.post(url, {
            'data': '{}',
        })
        # Should error due to missing slug field
        eq_(response.status_code, 400)

        response = self.client.post(url, {
            'slug': 'does_not_exist',
            'data': '{}',
        })
        eq_(response.status_code, 404)

        response = self.client.post(url, {
            'slug': event.slug,
            'data': '{}',
        })

        edit = PopcornEdit.objects.get(
            event=event,
            status=PopcornEdit.STATUS_PENDING,
        )

        eq_(response.status_code, 200)
        eq_(edit.id, json.loads(response.content)['id'])

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_vidly_webhook(self, p_urllib2):
        xml_string = SAMPLE_MEDIA_RESULT_SUCCESS
        success_xml = xmltodict.parse(xml_string)

        url = reverse('popcorn:vidly_webhook')
        task = success_xml['Response']['Result']['Task']
        tag = task['MediaShortLink']
        file_url = task['SourceFile']

        def make_mock_request(url, querystring):
            return mock.MagicMock()

        def mocked_urlopen(request):
            xml_string = get_custom_XML(
                tag=tag,
                status='Finished',
                private='false'
            )
            return StringIO(xml_string)

        p_urllib2.Request.side_effect = make_mock_request
        p_urllib2.urlopen = mocked_urlopen

        event = Event.objects.get(title='Test event')
        event.template.name = 'this is a vid.ly video'
        event.template.save()

        event.template_environment = {'tag': tag}
        event.save()

        vidly_submission = VidlySubmission.objects.create(
            event=event,
            url=file_url,
            tag=tag,
            token_protection=False
        )

        response = self.client.post(url, {'xml': xml_string})
        eq_(response.status_code, 200)
        eq_('OK\n', response.content)

        # Check that submission was created
        vidly_submission = VidlySubmission.objects.get(id=vidly_submission.id)
        ok_(vidly_submission.finished)

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_vidly_webhook_input_error(self, p_urllib2):
        def make_mock_request(url, querystring):
            return mock.MagicMock()

        def mocked_urlopen(request):
            xml_string = get_custom_XML(
                tag='abc123',
                status='Finished',
                private='false'
            )
            return StringIO(xml_string)

        p_urllib2.Request.side_effect = make_mock_request
        p_urllib2.urlopen = mocked_urlopen

        url = reverse('popcorn:vidly_webhook')

        response = self.client.post(url)
        eq_(response.status_code, 400)
        eq_("no 'xml'", response.content)

        response = self.client.post(url, {'xml': '<bad < xml}'})
        eq_(response.status_code, 400)
        eq_("Bad 'xml'", response.content)

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_vidly_webhook_404(self, p_urllib2):
        xml_string = SAMPLE_MEDIA_RESULT_SUCCESS

        def make_mock_request(url, querystring):
            return mock.MagicMock()

        def mocked_urlopen(request):
            xml_string = get_custom_XML(
                tag='abc123',
                status='Finished',
                private='false'
            )
            return StringIO(xml_string)

        p_urllib2.Request.side_effect = make_mock_request
        p_urllib2.urlopen = mocked_urlopen

        url = reverse('popcorn:vidly_webhook')

        response = self.client.post(url, {'xml': xml_string})
        eq_(response.status_code, 404)

    @override_settings(ADMINS=(('F', 'foo@bar.com'), ('B', 'bar@foo.com')))
    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_vidly_webhook_status_error(self, p_urllib2):
        xml_string = SAMPLE_MEDIA_RESULT_FAILED
        success_xml = xmltodict.parse(xml_string)

        def make_mock_request(url, querystring):
            return mock.MagicMock()

        def mocked_urlopen(request):
            xml_string = get_custom_XML(
                tag=task['MediaShortLink'],
                status='Error',
                private='false'
            )
            return StringIO(xml_string)

        p_urllib2.Request.side_effect = make_mock_request
        p_urllib2.urlopen = mocked_urlopen

        url = reverse('popcorn:vidly_webhook')
        task = success_xml['Response']['Result']['Task']
        tag = task['MediaShortLink']
        file_url = task['SourceFile']

        event = Event.objects.get(title='Test event')
        event.template.name = 'this is a vid.ly video'
        event.template.save()

        event.template_environment = {'tag': tag}
        event.save()

        VidlySubmission.objects.create(
            event=event,
            url=file_url,
            tag=tag,
            token_protection=False
        )

        response = self.client.post(url, {'xml': xml_string})
        eq_(response.status_code, 200)
        eq_('OK\n', response.content)

        email_sent = mail.outbox[-1]
        ok_(tag in email_sent.subject)

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_edit_status_and_revert(self, p_urllib2):

        def make_mock_request(url, querystring):
            return mock.MagicMock()

        def mocked_urlopen(request):
            xml_string = get_custom_XML(
                tag='xyz123',  # the original
                status='Finished',
            )
            return StringIO(xml_string)

        p_urllib2.Request.side_effect = make_mock_request
        p_urllib2.urlopen = mocked_urlopen

        # You arrive on the status page after you've done an edit
        # or because the event has an ongoing edit
        event = Event.objects.get(title='Test event')
        assert not VidlySubmission.objects.filter(event=event).exists()
        then = timezone.now() - datetime.timedelta(days=1)
        VidlySubmission.objects.create(
            event=event,
            tag='xyz123',
            url='https://file.com/move.mov',
            submission_time=then,
            hd=True,
            finished=then + datetime.timedelta(seconds=100)
        )
        template, = Template.objects.all()
        template.name = 'Vid.ly'
        template.save()
        event.template_environment = {'tag': 'xyz123'}
        event.template = template
        event.save()

        url = reverse('popcorn:edit_status', args=(event.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 302)
        user = self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # because there are no edits to revert to
        ok_('Revert to this version' not in response.content)

        # let's add 2 more edits
        edit1 = PopcornEdit.objects.create(
            event=event,
            user=user,
            upload=None,
            status=PopcornEdit.STATUS_PENDING,
            data={'fancy': 'edits'},
        )
        assert edit1.is_active
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # because there are no edits to revert to
        ok_('Revert to this version' not in response.content)
        ok_('<b>Pending</b>' in response.content)

        # Suppose we start processing it
        edit1.status = PopcornEdit.STATUS_PROCESSING
        edit1.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # because there are no edits to revert to
        ok_('Revert to this version' not in response.content)
        ok_('<b>Pending</b>' not in response.content)
        ok_('<b>Processing</b>' in response.content)

        # Now let's suppose all goes well and it uploads a file and
        # everything is hunky dory.
        upload1 = Upload.objects.create(
            event=event,
            url='http://files.com/edit1.webm',
            size=1234,
            upload_time=10,  # 10 seconds to upload
            user=user,
        )
        submission1 = VidlySubmission.objects.create(
            event=event,
            url='http://files.com/edit1.webm',
            tag='abc123',
            hd=True,
        )
        edit1.upload = upload1
        edit1.status = PopcornEdit.STATUS_SUCCESS
        edit1.save()

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Revert to this version' not in response.content)
        ok_('Waiting for transcoding to finish' in response.content)

        # suppose now that the transcoding does finish!
        submission1.finished = timezone.now()
        submission1.save()
        event.template_environment['tag'] = submission1.tag
        event.save()

        response = self.client.get(url)
        eq_(response.status_code, 200)
        # Now we should be able to reverse to the original
        ok_('Revert to this version' in response.content)
        ok_('<button name="tag" value="xyz123">' in response.content)

        # let's revert to the original
        url = reverse('popcorn:revert', args=(event.slug,))
        response = self.client.post(url)
        eq_(response.status_code, 400)

        response = self.client.post(url, {'tag': 'xyz123'})
        eq_(response.status_code, 302)

        # reload edit1
        edit1 = PopcornEdit.objects.get(id=edit1.id)
        ok_(not edit1.is_active)
