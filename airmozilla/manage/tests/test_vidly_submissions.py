import datetime
import urllib
from cStringIO import StringIO

import mock
from nose.tools import ok_, eq_

from django.utils import timezone

from airmozilla.main.models import Event, VidlySubmission
from airmozilla.manage import vidly_submissions
from airmozilla.base.tests.testbase import DjangoTestCase


class TestVidlySubmissions(DjangoTestCase):

    def test_parse_non_iso_date(self):
        timestr = '2015-08-05 19:41:05'
        result = vidly_submissions.parse_non_iso_date(timestr)
        eq_(result, datetime.datetime(
            2015, 8, 5, 19, 41, 5, tzinfo=timezone.UTC()
        ))

    @mock.patch('urllib2.urlopen')
    def test_resubmit_failures_nothing_done(self, p_urlopen):

        def mocked_urlopen(request):
            xml_string = urllib.unquote_plus(request.data)
            if 'GetMediaList' in xml_string:
                xml_output = (
                    '<?xml version="1.0"?>'
                    '<Response><Message>OK</Message>'
                    '<MessageCode>7.4</MessageCode><Success>'
                    '<Media><MediaShortLink>abc123</MediaShortLink>'
                    '<VanityLink/>'
                    '<Notify>vvm@spb-team.com</Notify>'
                    '<Created>2011-12-25 18:45:56</Created>'
                    '<Duration>350.75</Duration>'
                    '<Updated>2012-11-28 14:05:07</Updated>'
                    '<Status>Error</Status>'
                    '<IsDeleted>false</IsDeleted>'
                    '<IsPrivate>false</IsPrivate>'
                    '<IsPrivateCDN>false</IsPrivateCDN>'
                    '<CDN>AWS</CDN></Media>'
                    '</Success></Response>'
                )
                return StringIO(xml_output.strip())
            raise NotImplementedError(xml_string)

        p_urlopen.side_effect = mocked_urlopen
        resubmitted = vidly_submissions.resubmit_failures(verbose=True)
        # Because there are no known VidlySubmissions so we can't
        # figure out which event it belongs to.
        ok_(not resubmitted)

        event = Event.objects.get(title='Test event')
        submission = VidlySubmission.objects.create(
            event=event,
            url='https://example.com/file.mov',
            hd=True,
            token_protection=False,
            tag='abc123',
            errored=timezone.now() - datetime.timedelta(seconds=1),
        )
        new_submission = VidlySubmission.objects.create(
            event=event,
            url=submission.url,
            hd=submission.hd,
            token_protection=submission.token_protection,
            tag='xyz123',
            # Not finished
        )

        resubmitted = vidly_submissions.resubmit_failures()
        # Because there is another submission that is more recent
        # than the failed one.
        ok_(not resubmitted)

        # let's delete that healthy one and put in another failed one
        new_submission.delete()

        VidlySubmission.objects.create(
            event=event,
            url=submission.url,
            hd=submission.hd,
            token_protection=submission.token_protection,
            tag='xyz123',
            errored=timezone.now()
        )

        resubmitted = vidly_submissions.resubmit_failures()
        # Because there is another submission that is more recent
        # than the failed one.
        ok_(not resubmitted)

    @mock.patch('urllib2.urlopen')
    def test_resubmit_failures_resubmitted(self, p_urlopen):

        def mocked_urlopen(request):
            xml_string = urllib.unquote_plus(request.data)
            if 'GetMediaList' in xml_string:
                xml_output = (
                    '<?xml version="1.0"?>'
                    '<Response><Message>OK</Message>'
                    '<MessageCode>7.4</MessageCode><Success>'
                    '<Media><MediaShortLink>abc123</MediaShortLink>'
                    '<VanityLink/>'
                    '<Notify>vvm@spb-team.com</Notify>'
                    '<Created>2011-12-25 18:45:56</Created>'
                    '<Duration>350.75</Duration>'
                    '<Updated>2012-11-28 14:05:07</Updated>'
                    '<Status>Error</Status>'
                    '<IsDeleted>false</IsDeleted>'
                    '<IsPrivate>false</IsPrivate>'
                    '<IsPrivateCDN>false</IsPrivateCDN>'
                    '<CDN>AWS</CDN></Media>'
                    '</Success></Response>'
                )
                return StringIO(xml_output.strip())
            if 'AddMedia' in xml_string:
                xml_output = """
                    <?xml version="1.0"?>
                    <Response>
                      <Message>All medias have been added.</Message>
                      <MessageCode>2.1</MessageCode>
                      <BatchID>47520</BatchID>
                      <Success>
                        <MediaShortLink>
                          <SourceFile>http://www.com/file.flv</SourceFile>
                          <ShortLink>xyz123</ShortLink>
                          <MediaID>13969839</MediaID>
                          <QRCode>http://vid.ly/8oxv6x/qrcodeimg</QRCode>
                          <HtmlEmbed>code code</HtmlEmbed>
                          <EmailEmbed>more code code</EmailEmbed>
                        </MediaShortLink>
                      </Success>
                    </Response>
                """
                return StringIO(xml_output.strip())
            raise NotImplementedError(xml_string)

        p_urlopen.side_effect = mocked_urlopen
        resubmitted = vidly_submissions.resubmit_failures(verbose=True)
        # Because there are no known VidlySubmissions so we can't
        # figure out which event it belongs to.
        ok_(not resubmitted)

        event = Event.objects.get(title='Test event')
        submission = VidlySubmission.objects.create(
            event=event,
            url='https://example.com/file.mov',
            hd=True,
            token_protection=False,
            tag='abc123',
            errored=timezone.now() - datetime.timedelta(seconds=1),
        )

        resubmitted = vidly_submissions.resubmit_failures()
        # Because there is another submission that is more recent
        # than the failed one.
        ok_(resubmitted)

        event = Event.objects.get(id=event.id)
        eq_(event.status, Event.STATUS_PROCESSING)
        other_submission, = VidlySubmission.objects.exclude(id=submission.id)
        eq_(other_submission.url, submission.url)
        eq_(other_submission.tag, 'xyz123')
        eq_(other_submission.hd, True)
        eq_(other_submission.token_protection, False)
