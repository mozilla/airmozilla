from cStringIO import StringIO

from nose.tools import ok_, eq_
import mock

from django.test import TestCase

from airmozilla.main.models import Event, Template, VidlySubmission
from airmozilla.manage import videoinfo


class _Response(object):
    def __init__(self, content, status_code=200):
        self.content = self.text = content
        self.status_code = status_code


class TestVideoinfo(TestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']
    # main_image = 'airmozilla/manage/tests/firefox.png'

    @mock.patch('airmozilla.manage.vidly.logging')
    @mock.patch('airmozilla.manage.vidly.urllib2')
    @mock.patch('requests.head')
    @mock.patch('subprocess.Popen')
    def test_fetch_duration(self, mock_popen, rhead, p_urllib2, p_logging):

        def mocked_urlopen(request):
            return StringIO("""
            <?xml version="1.0"?>
            <Response>
              <Message>OK</Message>
              <MessageCode>7.4</MessageCode>
              <Success>
                <MediaShortLink>xxx999</MediaShortLink>
                <Token>MXCsxINnVtycv6j02ZVIlS4FcWP</Token>
              </Success>
            </Response>
            """)

        p_urllib2.urlopen = mocked_urlopen

        def mocked_head(url, **options):
            return _Response(
                '',
                200
            )

        rhead.side_effect = mocked_head

        ffmpeged_urls = []

        def mocked_popen(command, **kwargs):
            # print (args, kwargs)
            url = command[2]
            ffmpeged_urls.append(url)

            class Inner:
                def communicate(self):

                    out = ''
                    if 'abc123' in url:
                        err = "bla bla"
                    elif 'xyz123' in url:
                        err = """
            Duration: 00:19:17.47, start: 0.000000, bitrate: 1076 kb/s
                        """
                    else:
                        raise NotImplementedError(url)
                    return out, err

            return Inner()

        mock_popen.side_effect = mocked_popen

        event = Event.objects.get(title='Test event')
        template = Template.objects.create(
            name='Vid.ly Something',
            content="{{ tag }}"
        )
        event.template = template
        event.template_environment = {'tag': 'abc123'}
        event.save()
        assert event.duration is None

        videoinfo.fetch_durations()
        event = Event.objects.get(id=event.id)
        assert event.duration is None

        # need to change to a different tag
        # and make sure it has a VidlySubmission
        VidlySubmission.objects.create(
            event=event,
            url='https://s3.com/asomething.mov',
            tag='xyz123',
            hd=True,
        )
        event.template_environment = {'tag': 'xyz123'}
        event.save()
        videoinfo.fetch_durations()
        event = Event.objects.get(id=event.id)
        eq_(event.duration, 1157)

        # let's change our mind and make it a private event
        event.privacy = Event.PRIVACY_COMPANY
        event.duration = None
        event.save()
        VidlySubmission.objects.create(
            event=event,
            url='https://s3.com/asomething.mov',
            tag='xxx9999',
            hd=True,
            token_protection=True
        )

        # this won't be different
        videoinfo.fetch_durations()
        event = Event.objects.get(id=event.id)
        eq_(event.duration, 1157)

        # now we can check which URLs were sent into the ffmpeg command
        first, second, third = ffmpeged_urls
        ok_('hd_mp4' not in first)
        ok_('hd_mp4' in second)
        ok_('token=' in third)
