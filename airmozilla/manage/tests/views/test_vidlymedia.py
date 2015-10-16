# -*- coding: utf-8 -*-

import json
import hashlib
import datetime
from cStringIO import StringIO

from nose.tools import eq_, ok_
import mock

from django.utils import timezone
from django.core.cache import cache
from django.core.urlresolvers import reverse

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

SAMPLE_MEDIA_SUBMITTED_XML = """<?xml version="1.0"?>
<Response>
<Message>All medias have been added.</Message>
<MessageCode>2.1</MessageCode>
<BatchID>661742</BatchID>
<Success>
<MediaShortLink>
<SourceFile>http://d1ac1bzf3lrf3c.cloudfront.net/file.mov</SourceFile>
<ShortLink>i3b3kx</ShortLink>
<MediaID>34848570</MediaID>
<QRCode>http://vid.ly/i3b3kx/qrcodeimg</QRCode>
<HtmlEmbed>code code code</HtmlEmbed>
<ResponsiveEmbed>code code code</ResponsiveEmbed>
<EmailEmbed>code code code</EmailEmbed>
</MediaShortLink>
</Success>
</Response>
""".strip()

SAMPLE_MEDIA_RESULT_FAILED = """
<?xml version="1.0"?>
<Response>
  <Result>
    <Task>
      <UserID>1559</UserID>
      <MediaShortLink>i3b3ky</MediaShortLink>
      <SourceFile>http://d1ac1bzf3lrf3c.cloudfront.net/file.jpg</SourceFile>
      <BatchID>661742</BatchID>
      <Status>Error</Status>
      <Private>false</Private>
      <PrivateCDN>false</PrivateCDN>
      <Created>2015-02-23 16:17:56</Created>
      <Updated>2015-02-23 16:55:14</Updated>
      <UserEmail>airmozilla@muzilla.com</UserEmail>
      <MediaInfo/>
      <Formats>
        <Format>
          <FormatName>mp4</FormatName>
          <Location>http://cf.cdn.vid.ly/i3b3ky/mp4.mp4</Location>
          <FileSize>0</FileSize>
          <Status>Error</Status>
          <Error>Encoding was not completed:</Error>
        </Format>
        <Format>
          <FormatName>webm</FormatName>
          <Location>http://cf.cdn.vid.ly/i3b3ky/webm.webm</Location>
          <FileSize>0</FileSize>
          <Status>Error</Status>
          <Error>Encoding was not completed:</Error>
        </Format>
      </Formats>
    </Task>
  </Result>
</Response>
""".strip()

SAMPLE_MEDIA_RESULT_SUCCESS = """
<?xml version="1.0"?>
<Response>
    <Result>
        <Task>
            <UserID>1559</UserID>
            <MediaShortLink>c9v8gx</MediaShortLink>
            <SourceFile>https://uploads.s3.amazonaws.com/20555.mov</SourceFile>
            <BatchID>661728</BatchID>
            <Status>Finished</Status>
            <Private>false</Private>
            <PrivateCDN>false</PrivateCDN>
            <Created>2015-02-23 15:58:27</Created>
            <Updated>2015-02-23 16:11:53</Updated>
            <UserEmail>airmozilla@mozilla.com</UserEmail>
            <MediaInfo>
                <bitrate>11136k</bitrate>
                <duration>9.84</duration>
                <audio_bitrate>64.0k</audio_bitrate>
                <audio_duration>9.838</audio_duration>
                <video_duration>9.84</video_duration>
                <video_codec>h264 (High)</video_codec>
                <size>1920x1080</size>
                <video_bitrate>11066k</video_bitrate>
                <audio_codec>aac</audio_codec>
                <audio_sample_rate>44100</audio_sample_rate>
                <audio_channels>1</audio_channels>
                <filesize>13697959</filesize>
                <frame_rate>29.98</frame_rate>
                <format>mpeg-4</format>
            </MediaInfo>
            <Formats>
            <Format>
                <FormatName>mp4</FormatName>
                <Location>http://cf.cdn.vid.ly/c9v8gx/mp4.mp4</Location>
                <FileSize>1063533</FileSize>
                <Status>Finished</Status>
                </Format>
            </Formats>
        </Task>
    </Result>
</Response>
""".strip()


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

        then = timezone.now() - datetime.timedelta(days=1)
        VidlySubmission.objects.create(
            event=event,
            tag='xyz000',
            submission_time=then,
            finished=then + datetime.timedelta(seconds=7)
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.title in response.content)
        ok_('7s' in response.content)

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
        )
        response = self.client.get(url, {
            'id': event.pk,
            'past_submission_info': True
        })
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        past = data['past_submission']
        eq_(past['url'], submission.url)
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
            if 'AddMediaLite' in request.data:
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
            'hd': True,
            'token_protection': False,  # observe!
        })
        eq_(response.status_code, 302)

        submission, = VidlySubmission.objects.filter(event=event)
        ok_(submission.url, 'http://better.com')
        ok_(submission.hd)
        # this gets forced on since the event is not public
        ok_(submission.token_protection)

        event = Event.objects.get(pk=event.pk)
        eq_(event.template_environment['tag'], '8oxv6x')

    @mock.patch('urllib2.urlopen')
    def test_vidly_media_resubmit_with_error(self, p_urlopen):

        def mocked_urlopen(request):
            if 'AddMediaLite' in request.data:
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
        ok_(submission.hd)
        ok_(not submission.token_protection)
        ok_(submission.submission_error)
        ok_('ble ble' in submission.submission_error)

        event = Event.objects.get(pk=event.pk)
        eq_(event.template_environment['tag'], 'abc123')  # the old one

    def test_vidly_media_webhook_gibberish(self):
        url = reverse('manage:vidly_media_webhook')
        eq_(self.client.get(url).status_code, 405)
        eq_(self.client.post(url).status_code, 400)
        eq_(self.client.post(url, {'xml': 'Not XML!'}).status_code, 400)

    def test_vidly_media_webhook_media_submitted(self):
        url = reverse('manage:vidly_media_webhook')
        response = self.client.post(url, {'xml': SAMPLE_MEDIA_SUBMITTED_XML})
        eq_(response.status_code, 200)
        eq_('OK\n', response.content)

    def test_vidly_media_webhook_media_failed(self):
        url = reverse('manage:vidly_media_webhook')
        response = self.client.post(url, {'xml': SAMPLE_MEDIA_RESULT_FAILED})
        eq_(response.status_code, 200)
        eq_('OK\n', response.content)

    def test_vidly_media_webhook_media_successful(self):
        url = reverse('manage:vidly_media_webhook')
        response = self.client.post(url, {'xml': SAMPLE_MEDIA_RESULT_SUCCESS})
        eq_(response.status_code, 200)
        eq_('OK\n', response.content)

    def test_vidly_media_timings(self):
        url = reverse('manage:vidly_media_timings')
        response = self.client.get(url)
        # Not much is happening on this page server side.
        # It just loads some javascript that loads some JSON
        eq_(response.status_code, 200)

    def test_vidly_media_timings_data(self):
        url = reverse('manage:vidly_media_timings_data')
        response = self.client.get(url)
        # Not much is happening on this page server side.
        # It just loads some javascript that loads some JSON
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['points'], [])
        eq_(data['slope'], None)

        event = Event.objects.get(title='Test event')
        event.duration = 60
        event.save()
        VidlySubmission.objects.create(
            event=event,
            submission_time=timezone.now(),
            finished=timezone.now() + datetime.timedelta(seconds=150),
        )
        VidlySubmission.objects.create(
            event=event,
            submission_time=timezone.now(),
            finished=timezone.now() + datetime.timedelta(seconds=100),
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['points'], [{'y': 150, 'x': 60}, {'y': 100, 'x': 60}])
        # Because the X value never changes you get a standard deviation
        # of 0 which means the slope can't be calculated
        eq_(data['slope'], None)

        other_event = Event.objects.create(
            duration=200,
            start_time=event.start_time,
        )
        VidlySubmission.objects.create(
            event=other_event,
            submission_time=timezone.now(),
            finished=timezone.now() + datetime.timedelta(seconds=300),
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['points'], [
            {'y': 150, 'x': 60},
            {'y': 100, 'x': 60},
            {'y': 300, 'x': 200},
        ])
        # Because the X value never changes you get a standard deviation
        # of 0 which means the slope can't be calculated
        eq_(data['slope'], 1.25)
