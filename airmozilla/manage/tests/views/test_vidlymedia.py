# -*- coding: utf-8 -*-
import json
import hashlib
from cStringIO import StringIO

from nose.tools import eq_, ok_
import mock

from django.core.cache import cache

from funfactory.urlresolvers import reverse

from airmozilla.main.models import (
    Event,
    Template,
    VidlySubmission
)
from airmozilla.manage.tests.test_vidly import (
    SAMPLE_XML,
    SAMPLE_MEDIALIST_XML,
    SAMPLE_INVALID_LINKS_XML,
    get_custom_XML
)
from .base import ManageTestCase


class TestVidlyMedia(ManageTestCase):

    def test_vidly_media(self):
        url = reverse('manage:vidly_media')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        event = Event.objects.get(title='Test event')
        ok_(event.title not in response.content)

        event.template = Template.objects.create(
            name='Vid.ly Something',
            content='<iframe>'
        )
        event.save()

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.title in response.content)

        # or the event might not yet have made the switch but already
        # has a VidlySubmission
        event.template = None
        event.save()

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.title not in response.content)

        VidlySubmission.objects.create(
            event=event,
            tag='xyz000'
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.title in response.content)

    def test_vidly_media_repeated_events(self):
        url = reverse('manage:vidly_media')
        event = Event.objects.get(title='Test event')

        event.template = Template.objects.create(
            name='Vid.ly Something',
            content='<iframe>'
        )
        event.save()

        response = self.client.get(url, {'repeated': 'event'})
        eq_(response.status_code, 200)
        ok_(event.title not in response.content)

        VidlySubmission.objects.create(
            event=event,
            tag='xyz001'
        )
        response = self.client.get(url, {'repeated': 'event'})
        eq_(response.status_code, 200)
        # still not because there's only one VidlySubmission
        ok_(event.title not in response.content)

        VidlySubmission.objects.create(
            event=event,
            tag='xyz002'
        )
        response = self.client.get(url, {'repeated': 'event'})
        eq_(response.status_code, 200)
        ok_(event.title in response.content)

        vidly_submissions_url = reverse(
            'manage:event_vidly_submissions',
            args=(event.id,)
        )
        ok_(vidly_submissions_url in response.content)

    @mock.patch('urllib2.urlopen')
    def test_vidly_media_with_status(self, p_urlopen):

        def mocked_urlopen(request):
            return StringIO(SAMPLE_MEDIALIST_XML.strip())

        p_urlopen.side_effect = mocked_urlopen

        url = reverse('manage:vidly_media')
        response = self.client.get(url, {'status': 'Error'})
        eq_(response.status_code, 200)

        event = Event.objects.get(title='Test event')
        ok_(event.title not in response.content)

        event.template = Template.objects.create(
            name='Vid.ly Something',
            content='<iframe>'
        )
        event.template_environment = {'tag': 'abc123'}
        event.save()

        response = self.client.get(url, {'status': 'Error'})
        eq_(response.status_code, 200)
        ok_(event.title in response.content)

    @mock.patch('urllib2.urlopen')
    def test_vidly_media_status(self, p_urlopen):

        def mocked_urlopen(request):
            return StringIO(SAMPLE_XML.strip())

        p_urlopen.side_effect = mocked_urlopen

        event = Event.objects.get(title='Test event')
        url = reverse('manage:vidly_media_status')
        response = self.client.get(url)
        eq_(response.status_code, 400)

        event.template = Template.objects.create(
            name='Vid.ly Something',
            content='<iframe>'
        )
        event.template_environment = {'tag': 'abc123'}
        event.save()

        response = self.client.get(url, {'id': 9999})
        eq_(response.status_code, 404)

        response = self.client.get(url, {'id': event.pk})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['status'], 'Finished')

    @mock.patch('urllib2.urlopen')
    def test_non_ascii_char_in_tag(self, p_urlopen):
        tag = u'kristján'

        def mocked_urlopen(request):
            return StringIO(get_custom_XML(tag=tag))

        p_urlopen.side_effect = mocked_urlopen

        event = Event.objects.get(title='Test event')

        event.template = Template.objects.create(
            name='Vid.ly Something',
            content='<iframe>'
        )
        event.template_environment = {'tag': tag}
        event.save()

        url = reverse('manage:vidly_media_status')
        response = self.client.get(url, {'id': event.pk, 'refresh': True})
        eq_(response.status_code, 200)

        cache_key = 'vidly-query-{md5}'.format(
            md5=hashlib.md5(tag.encode('utf8')).hexdigest()).strip()
        ok_(cache.get(cache_key))

    @mock.patch('urllib2.urlopen')
    def test_vidly_media_status_not_vidly_template(self, p_urlopen):

        def mocked_urlopen(request):
            return StringIO(SAMPLE_XML.strip())

        p_urlopen.side_effect = mocked_urlopen

        event = Event.objects.get(title='Test event')
        url = reverse('manage:vidly_media_status')
        response = self.client.get(url)
        eq_(response.status_code, 400)

        event.template = Template.objects.create(
            name='EdgeCast',
            content='<iframe>'
        )
        event.template_environment = {'other': 'stuff'}
        event.save()

        VidlySubmission.objects.create(
            event=event,
            tag='abc123'
        )

        response = self.client.get(url, {'id': event.pk})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['status'], 'Finished')

    @mock.patch('urllib2.urlopen')
    def test_vidly_media_info(self, p_urlopen):

        sent_queries = []

        def mocked_urlopen(request):
            sent_queries.append(True)
            return StringIO(SAMPLE_XML.strip())

        p_urlopen.side_effect = mocked_urlopen

        event = Event.objects.get(title='Test event')
        url = reverse('manage:vidly_media_info')
        response = self.client.get(url)
        eq_(response.status_code, 400)

        event.template = Template.objects.create(
            name='Vid.ly Something',
            content='<iframe>'
        )
        event.template_environment = {'foo': 'bar'}
        event.save()

        response = self.client.get(url, {'id': 9999})
        eq_(response.status_code, 404)

        response = self.client.get(url, {'id': event.pk})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        fields = data['fields']
        ok_([x for x in fields if x['key'] == '*Note*'])

        event.template_environment = {'tag': 'abc123'}
        event.save()

        response = self.client.get(url, {'id': event.pk})
        eq_(response.status_code, 200)
        eq_(len(sent_queries), 1)

        data = json.loads(response.content)
        fields = data['fields']
        ok_(
            [x for x in fields
             if x['key'] == 'Status' and x['value'] == 'Finished']
        )

        # a second time and it should be cached
        response = self.client.get(url, {'id': event.pk})
        eq_(response.status_code, 200)
        eq_(len(sent_queries), 1)

        # unless you set this
        response = self.client.get(url, {'id': event.pk, 'refresh': 1})
        eq_(response.status_code, 200)
        eq_(len(sent_queries), 2)

    @mock.patch('urllib2.urlopen')
    def test_vidly_media_info_with_error(self, p_urlopen):

        sent_queries = []

        def mocked_urlopen(request):
            sent_queries.append(True)
            return StringIO(SAMPLE_INVALID_LINKS_XML.strip())

        p_urlopen.side_effect = mocked_urlopen

        event = Event.objects.get(title='Test event')
        url = reverse('manage:vidly_media_info')
        response = self.client.get(url)
        eq_(response.status_code, 400)

        event.template = Template.objects.create(
            name='Vid.ly Something',
            content='<iframe>'
        )
        event.template_environment = {'tag': 'bbb1234'}
        event.save()

        response = self.client.get(url, {'id': event.pk})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['ERRORS'], ['Tag (bbb1234) not found in Vid.ly'])

    @mock.patch('urllib2.urlopen')
    def test_vidly_media_info_with_past_submission_info(self, p_urlopen):

        def mocked_urlopen(request):
            return StringIO(SAMPLE_XML.strip())

        p_urlopen.side_effect = mocked_urlopen

        event = Event.objects.get(title='Test event')
        url = reverse('manage:vidly_media_info')

        event.template = Template.objects.create(
            name='Vid.ly Something',
            content='<iframe>'
        )
        event.template_environment = {'tag': 'abc123'}
        event.save()

        response = self.client.get(url, {
            'id': event.pk,
        })
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        ok_(data['fields'])
        ok_(data['past_submission'])
        eq_(
            data['past_submission']['url'],
            'http://videos.mozilla.org/bla.f4v'
        )
        eq_(
            data['past_submission']['email'],
            'airmozilla@mozilla.com'
        )
        previous_past_submission = data['past_submission']

        response = self.client.get(url, {
            'id': event.pk,
            'past_submission_info': True
        })
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        ok_(data['fields'])
        ok_(data['past_submission'])
        eq_(previous_past_submission, data['past_submission'])

        submission = VidlySubmission.objects.create(
            event=event,
            url='http://something.com',
            hd=True,
            token_protection=True,
            email='test@example.com'
        )
        response = self.client.get(url, {
            'id': event.pk,
            'past_submission_info': True
        })
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        past = data['past_submission']
        eq_(past['url'], submission.url)
        eq_(past['email'], submission.email)
        ok_(submission.hd)
        ok_(submission.token_protection)

    @mock.patch('urllib2.urlopen')
    def test_vidly_media_status_with_caching(self, p_urlopen):

        sent_queries = []

        def mocked_urlopen(request):
            sent_queries.append(True)
            return StringIO(get_custom_XML(tag='aaa1234'))

        p_urlopen.side_effect = mocked_urlopen

        event = Event.objects.get(title='Test event')
        url = reverse('manage:vidly_media_status')

        event.template = Template.objects.create(
            name='Vid.ly Something',
            content='<iframe>'
        )
        event.template_environment = {'foo': 'bar'}
        event.save()

        response = self.client.get(url, {'id': event.pk})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data, {})
        eq_(len(sent_queries), 0)

        event.template_environment = {'tag': 'aaa1234'}
        event.save()

        response = self.client.get(url, {'id': event.pk})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data, {'status': 'Finished'})
        eq_(len(sent_queries), 1)

        # do it again, it should be cached
        response = self.client.get(url, {'id': event.pk})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data, {'status': 'Finished'})
        eq_(len(sent_queries), 1)

        response = self.client.get(url, {'id': event.pk, 'refresh': 'true'})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data, {'status': 'Finished'})
        eq_(len(sent_queries), 2)

    @mock.patch('urllib2.urlopen')
    def test_vidly_media_resubmit(self, p_urlopen):

        sent_queries = []

        def mocked_urlopen(request):
            sent_queries.append(True)
            if 'AddMedia' in request.data:
                return StringIO("""
                <?xml version="1.0"?>
                <Response>
                  <Message>All medias have been added.</Message>
                  <MessageCode>2.1</MessageCode>
                  <BatchID>47520</BatchID>
                  <Success>
                    <MediaShortLink>
                      <SourceFile>http://www.com/file.flv</SourceFile>
                      <ShortLink>8oxv6x</ShortLink>
                      <MediaID>13969839</MediaID>
                      <QRCode>http://vid.ly/8oxv6x/qrcodeimg</QRCode>
                      <HtmlEmbed>code code</HtmlEmbed>
                      <EmailEmbed>more code code</EmailEmbed>
                    </MediaShortLink>
                  </Success>
                </Response>
                """.strip())
            elif 'DeleteMedia' in request.data:
                return StringIO("""
                <?xml version="1.0"?>
                <Response>
                  <Message>Success</Message>
                  <MessageCode>0.0</MessageCode>
                  <Success>
                    <MediaShortLink>8oxv6x</MediaShortLink>
                  </Success>
                  <Errors>
                    <Error>
                      <SourceFile>http://www.com</SourceFile>
                      <ErrorCode>1</ErrorCode>
                      <Description>ErrorDescriptionK</Description>
                      <Suggestion>ErrorSuggestionK</Suggestion>
                    </Error>
                  </Errors>
                </Response>
                """.strip())
            else:
                raise NotImplementedError(request.data)

        p_urlopen.side_effect = mocked_urlopen

        event = Event.objects.get(title='Test event')
        event.privacy = Event.PRIVACY_COMPANY
        url = reverse('manage:vidly_media_resubmit')

        event.template = Template.objects.create(
            name='Vid.ly Something',
            content='<iframe>'
        )
        event.template_environment = {'tag': 'abc123'}
        event.save()

        response = self.client.post(url, {
            'id': event.pk,
        })
        eq_(response.status_code, 200)
        ok_('errorlist' in response.content)

        ok_(not VidlySubmission.objects.filter(event=event))

        response = self.client.post(url, {
            'id': event.pk,
            'url': 'http://better.com',
            'email': 'peter@example.com',
            'hd': True,
            'token_protection': False,  # observe!
        })
        eq_(response.status_code, 302)

        submission, = VidlySubmission.objects.filter(event=event)
        ok_(submission.url, 'http://better.com')
        ok_(submission.email, 'peter@example.com')
        ok_(submission.hd)
        # this gets forced on since the event is not public
        ok_(submission.token_protection)

        event = Event.objects.get(pk=event.pk)
        eq_(event.template_environment['tag'], '8oxv6x')

    @mock.patch('urllib2.urlopen')
    def test_vidly_media_resubmit_with_error(self, p_urlopen):

        def mocked_urlopen(request):
            if 'AddMedia' in request.data:
                return StringIO("""
                <?xml version="1.0"?>
            <Response>
              <Message>Error</Message>
              <MessageCode>0.0</MessageCode>
              <Errors>
                <Error>
                  <ErrorCode>0.0</ErrorCode>
                  <ErrorName>Error message</ErrorName>
                  <Description>bla bla</Description>
                  <Suggestion>ble ble</Suggestion>
                </Error>
              </Errors>
            </Response>
                """.strip())
            else:
                raise NotImplementedError(request.data)

        p_urlopen.side_effect = mocked_urlopen

        event = Event.objects.get(title='Test event')
        url = reverse('manage:vidly_media_resubmit')

        event.template = Template.objects.create(
            name='Vid.ly Something',
            content='<iframe>'
        )
        event.template_environment = {'tag': 'abc123'}
        event.save()

        response = self.client.post(url, {
            'id': event.pk,
            'url': 'http://better.com',
            'email': 'peter@example.com',
            'hd': True
        })
        eq_(response.status_code, 302)

        submission, = VidlySubmission.objects.filter(event=event)
        ok_(submission.url, 'http://better.com')
        ok_(submission.email, 'peter@example.com')
        ok_(submission.hd)
        ok_(not submission.token_protection)
        ok_(submission.submission_error)
        ok_('ble ble' in submission.submission_error)

        event = Event.objects.get(pk=event.pk)
        eq_(event.template_environment['tag'], 'abc123')  # the old one
