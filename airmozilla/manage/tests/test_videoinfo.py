import os
import sys
import shutil
import tempfile
from cStringIO import StringIO

from nose.tools import ok_, eq_
import mock

from django.conf import settings
from django.core.cache import cache

from airmozilla.main.models import Event, Template, VidlySubmission, Picture
from airmozilla.manage import videoinfo
from airmozilla.base.tests.testbase import DjangoTestCase, Response


class TestVideoinfo(DjangoTestCase):
    sample_jpg = 'airmozilla/manage/tests/presenting.jpg'
    sample_jpg2 = 'airmozilla/manage/tests/tucker.jpg'

    _original_temp_directory_name = settings.SCREENCAPTURES_TEMP_DIRECTORY_NAME

    def setUp(self):
        super(TestVideoinfo, self).setUp()
        settings.SCREENCAPTURES_TEMP_DIRECTORY_NAME = (
            'test_' + self._original_temp_directory_name
        )

    def tearDown(self):
        cache.clear()
        assert settings.SCREENCAPTURES_TEMP_DIRECTORY_NAME.startswith('test_')
        temp_dir = os.path.join(
            tempfile.gettempdir(),
            settings.SCREENCAPTURES_TEMP_DIRECTORY_NAME
        )
        if os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir)
        super(TestVideoinfo, self).tearDown()

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
            return Response(
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

    @mock.patch('requests.head')
    @mock.patch('subprocess.Popen')
    def test_fetch_duration_oserror(self, mock_popen, rhead):

        def mocked_head(url, **options):
            return Response(
                '',
                200
            )

        rhead.side_effect = mocked_head

        def mocked_popen(command, **kwargs):

            class Inner:
                def communicate(self):
                    raise OSError('Something Bad')

            return Inner()

        mock_popen.side_effect = mocked_popen

        event = Event.objects.get(title='Test event')
        video_url = 'https://example.com/file.mov'
        try:
            videoinfo.fetch_duration(event, video_url=video_url)
            raise AssertionError("not supposed to happen")
        except OSError as exception:
            message = str(exception)
            ok_('Something Bad' in message)
            ok_('ffmpeg -i %s' % video_url in message)

    @mock.patch('airmozilla.manage.vidly.logging')
    @mock.patch('airmozilla.manage.vidly.urllib2')
    @mock.patch('requests.head')
    @mock.patch('subprocess.Popen')
    def test_fetch_duration_token_protected_public_event(
        self, mock_popen, rhead, p_urllib2, p_logging
    ):

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
            return Response(
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
                    assert 'xyz123' in url
                    out = ''
                    err = """
            Duration: 00:19:17.47, start: 0.000000, bitrate: 1076 kb/s
                    """
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
        assert event.privacy == Event.PRIVACY_PUBLIC
        assert event.duration is None

        # need to change to a different tag
        # and make sure it has a VidlySubmission
        VidlySubmission.objects.create(
            event=event,
            url='https://s3.com/asomething.mov',
            tag='xyz123',
            token_protection=True,  # Note!~
            hd=True,
        )
        event.template_environment = {'tag': 'xyz123'}
        event.save()
        videoinfo.fetch_durations()
        event = Event.objects.get(id=event.id)
        eq_(event.duration, 1157)
        url, = ffmpeged_urls
        ok_('&token=' in url)

    @mock.patch('airmozilla.manage.vidly.logging')
    @mock.patch('airmozilla.manage.vidly.urllib2')
    @mock.patch('requests.head')
    def test_fetch_duration_fail_to_fetch(
        self, rhead, p_urllib2, p_logging
    ):

        def mocked_head(url, **options):
            return Response(
                'Not Found',
                404
            )

        rhead.side_effect = mocked_head

        event = Event.objects.get(title='Test event')
        template = Template.objects.create(
            name='Vid.ly Something',
            content="{{ tag }}"
        )
        event.template = template
        event.template_environment = {'tag': 'abc123'}
        event.save()
        assert event.duration is None

        buffer = StringIO()
        sys.stdout = buffer
        try:
            videoinfo.fetch_durations()
        finally:
            sys.stdout = sys.__stdout__

        event = Event.objects.get(id=event.id)
        eq_(event.duration, None)  # because it failed
        output = buffer.getvalue()
        ok_('404' in output)

    @mock.patch('airmozilla.manage.vidly.logging')
    @mock.patch('airmozilla.manage.vidly.urllib2')
    @mock.patch('requests.head')
    def test_fetch_duration_fail_to_fetch_not_video(
        self, rhead, p_urllib2, p_logging
    ):

        def mocked_head(url, **options):
            return Response(
                '<html>',
                200,
                headers={
                    'Content-Type': 'text/html; charset=utf-8'
                }
            )

        rhead.side_effect = mocked_head

        event = Event.objects.get(title='Test event')
        template = Template.objects.create(
            name='Vid.ly Something',
            content="{{ tag }}"
        )
        event.template = template
        event.template_environment = {'tag': 'abc123'}
        event.save()
        assert event.duration is None

        buffer = StringIO()
        sys.stdout = buffer
        try:
            videoinfo.fetch_durations()
        finally:
            sys.stdout = sys.__stdout__

        event = Event.objects.get(id=event.id)
        eq_(event.duration, None)  # because it failed
        output = buffer.getvalue()
        ok_(
            '{0}/abc123?content=video&format=mp4 is a '
            'text/html document'.format(settings.VIDLY_BASE_URL) in output
        )

    @mock.patch('airmozilla.manage.vidly.logging')
    @mock.patch('airmozilla.manage.vidly.urllib2')
    @mock.patch('requests.head')
    def test_fetch_duration_fail_to_fetch_0_content_length(
        self, rhead, p_urllib2, p_logging
    ):

        def mocked_head(url, **options):
            return Response(
                '<html>',
                200,
                headers={
                    'Content-Length': '0'
                }
            )

        rhead.side_effect = mocked_head

        event = Event.objects.get(title='Test event')
        template = Template.objects.create(
            name='Vid.ly Something',
            content="{{ tag }}"
        )
        event.template = template
        event.template_environment = {'tag': 'abc123'}
        event.save()
        assert event.duration is None

        buffer = StringIO()
        sys.stdout = buffer
        try:
            videoinfo.fetch_durations()
        finally:
            sys.stdout = sys.__stdout__

        event = Event.objects.get(id=event.id)
        eq_(event.duration, None)  # because it failed
        output = buffer.getvalue()
        ok_(
            '{0}/abc123?content=video&format=mp4 has a 0 byte '
            'Content-Length'.format(settings.VIDLY_BASE_URL) in output
        )

    @mock.patch('airmozilla.manage.vidly.logging')
    @mock.patch('airmozilla.manage.vidly.urllib2')
    @mock.patch('requests.head')
    @mock.patch('requests.get')
    @mock.patch('subprocess.Popen')
    def test_fetch_duration_save_locally(
        self, mock_popen, rget, rhead, p_urllib2, p_logging
    ):

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
            if 'file.mpg' in url:
                return Response(
                    '',
                    200
                )
            return Response(
                '',
                302,
                headers={
                    'Location': 'https://otherplace.com/file.mpg'
                }
            )

        rhead.side_effect = mocked_head

        def mocked_get(url, **options):
            return Response(
                '0' * 100000,
                200,
                headers={
                    'Content-Length': 100000
                }
            )

        rget.side_effect = mocked_get

        ffmpeged_urls = []

        def mocked_popen(command, **kwargs):

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

        videoinfo.fetch_durations(save_locally=True)
        event = Event.objects.get(id=event.id)
        assert event.duration is None

        ffmpeged_url, = ffmpeged_urls
        ok_(ffmpeged_url.endswith('abc123.mp4'))

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
        videoinfo.fetch_durations(save_locally=True)
        event = Event.objects.get(id=event.id)
        eq_(event.duration, 1157)

        ffmpeged_url, ffmpeged_url2 = ffmpeged_urls
        ok_(ffmpeged_url.endswith('abc123.mp4'))
        ok_(ffmpeged_url2.endswith('xyz123.mp4'))

    @mock.patch('airmozilla.manage.vidly.logging')
    @mock.patch('airmozilla.manage.vidly.urllib2')
    @mock.patch('requests.head')
    @mock.patch('requests.get')
    @mock.patch('subprocess.Popen')
    def test_fetch_duration_save_locally_some(
        self, mock_popen, rget, rhead, p_urllib2, p_logging
    ):
        """This time we're going to have two events to ponder.
        One is public and one is staff only.
        With passing `save_locally_some` it should do
        `ffmpeg -i http://url...` on the public one and
        `wget https://...; ffmpeg -i /local/file.mpg` on the private one.
        """

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
            # print "HEAD URL", url
            if 'file.mp4' in url:
                return Response(
                    '',
                    200
                )
            return Response(
                '',
                302,
                headers={
                    'Location': 'https://otherplace.com/file.mp4'
                }
            )

        rhead.side_effect = mocked_head

        def mocked_get(url, **options):
            # print "GET URL", url
            return Response(
                '0' * 100000,
                200,
                headers={
                    'Content-Length': 100000
                }
            )

        rget.side_effect = mocked_get

        ffmpeged_urls = []

        def mocked_popen(command, **kwargs):

            url = command[2]
            ffmpeged_urls.append(url)

            class Inner:
                def communicate(self):
                    out = ''
                    if 'otherplace.com/file.mp4' in url:
                        err = """
            Duration: 01:05:00.47, start: 0.000000, bitrate: 1076 kb/s
                        """
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
        assert event.privacy == Event.PRIVACY_PUBLIC
        event.save()

        event2 = Event.objects.create(
            slug='slug2',
            title=event.title,
            start_time=event.start_time,
            placeholder_img=event.placeholder_img,
            privacy=Event.PRIVACY_COMPANY,
            template=template,
            template_environment={'tag': 'xyz123'},
        )

        videoinfo.fetch_durations(save_locally_some=True)
        event = Event.objects.get(id=event.id)
        eq_(event.duration, 3900)

        event2 = Event.objects.get(id=event2.id)
        eq_(event2.duration, 1157)

        ffmpeged_urls.sort()
        ffmpeged_url1, ffmpeged_url2 = ffmpeged_urls
        ok_(ffmpeged_url1.endswith('xyz123.mp4'))
        ok_(ffmpeged_url1.startswith('/'))
        ok_(ffmpeged_url2.endswith('file.mp4'))
        ok_(ffmpeged_url2.startswith('http://'))

    @mock.patch('airmozilla.manage.vidly.logging')
    @mock.patch('airmozilla.manage.vidly.urllib2')
    @mock.patch('requests.head')
    @mock.patch('requests.get')
    @mock.patch('subprocess.Popen')
    def test_fetch_duration_save_locally_some_by_vidly_submission(
        self, mock_popen, rget, rhead, p_urllib2, p_logging
    ):
        """This time we're going to have two events to ponder.
        One is public and one is staff only.
        With passing `save_locally_some` it should do
        `ffmpeg -i http://url...` on the public one and
        `wget https://...; ffmpeg -i /local/file.mpg` on the private one.
        """

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
            # print "HEAD URL", url
            if 'file.mp4' in url:
                return Response(
                    '',
                    200
                )
            return Response(
                '',
                302,
                headers={
                    'Location': 'https://otherplace.com/file.mp4'
                }
            )

        rhead.side_effect = mocked_head

        def mocked_get(url, **options):
            # print "GET URL", url
            return Response(
                '0' * 100000,
                200,
                headers={
                    'Content-Length': 100000
                }
            )

        rget.side_effect = mocked_get

        ffmpeged_urls = []

        def mocked_popen(command, **kwargs):

            url = command[2]
            ffmpeged_urls.append(url)

            class Inner:
                def communicate(self):
                    out = ''
                    if 'abc123.mp4' in url and url.startswith('/'):
                        err = """
            Duration: 01:05:00.47, start: 0.000000, bitrate: 1076 kb/s
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
        assert event.privacy == Event.PRIVACY_PUBLIC
        event.save()

        # The event is public but the relevant vidly submission
        # for it says it requires a token.
        VidlySubmission.objects.create(
            event=event,
            tag='somethingelse',
        )
        VidlySubmission.objects.create(
            event=event,
            tag='abc123',
            token_protection=True,
        )

        videoinfo.fetch_durations(save_locally_some=True)
        event = Event.objects.get(id=event.id)
        eq_(event.duration, 3900)
        ok_('http://otherplace.com/file.mp4' not in ffmpeged_urls)
        filename, = ffmpeged_urls
        ok_(filename.endswith('abc123.mp4'))

    @mock.patch('airmozilla.manage.vidly.logging')
    @mock.patch('airmozilla.manage.vidly.urllib2')
    @mock.patch('requests.head')
    @mock.patch('subprocess.Popen')
    def test_fetch_duration_ogg_videos(
        self, mock_popen, rhead, p_urllib2, p_logging
    ):

        def mocked_head(url, **options):
            return Response(
                '',
                200
            )

        rhead.side_effect = mocked_head

        ffmpeged_urls = []

        def mocked_popen(command, **kwargs):
            url = command[2]
            assert url.endswith('foo.ogg')
            ffmpeged_urls.append(url)

            class Inner:
                def communicate(self):
                    err = """
                    Duration: 00:10:31.52, start: 0.000000, bitrate: 77 kb/s
                    """
                    out = ''
                    return out, err

            return Inner()

        mock_popen.side_effect = mocked_popen

        event = Event.objects.get(title='Test event')
        template = Template.objects.create(
            name='Ogg Video',
            content='<source src="{{ url }}" type="video/ogg" />'
        )
        event.template = template
        event.template_environment = {'url': 'http://videos.m.org/foo.ogg'}
        event.save()
        assert event.duration is None

        videoinfo.fetch_durations()
        event = Event.objects.get(id=event.id)
        eq_(event.duration, 631)

    @mock.patch('airmozilla.manage.vidly.logging')
    @mock.patch('airmozilla.manage.vidly.urllib2')
    @mock.patch('requests.head')
    @mock.patch('subprocess.Popen')
    def test_fetch_screencapture(self, mock_popen, rhead, p_urllib2, p_log):

        assert Picture.objects.all().count() == 0, Picture.objects.all()

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
            return Response(
                '',
                200
            )

        rhead.side_effect = mocked_head

        ffmpeged_urls = []

        sample_jpg = self.sample_jpg
        sample_jpg2 = self.sample_jpg2

        def mocked_popen(command, **kwargs):
            url = command[4]
            ffmpeged_urls.append(url)
            destination = command[-1]
            assert os.path.isdir(os.path.dirname(destination))

            class Inner:
                def communicate(self):
                    out = err = ''
                    if 'xyz123' in url:
                        if '01.jpg' in destination:
                            shutil.copyfile(sample_jpg, destination)
                        else:
                            shutil.copyfile(sample_jpg2, destination)
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
        event.save()
        assert event.duration is None

        videoinfo.fetch_screencaptures()
        assert not ffmpeged_urls  # because no event has a duration yet
        event.duration = 1157
        event.save()

        # Make sure it has a HD VidlySubmission
        VidlySubmission.objects.create(
            event=event,
            url='https://s3.com/asomething.mov',
            tag='xyz123',
            hd=True,
        )
        event.template_environment = {'tag': 'xyz123'}
        event.save()
        videoinfo.fetch_screencaptures()
        assert ffmpeged_urls
        no_screencaptures = settings.SCREENCAPTURES_NO_PICTURES
        eq_(Picture.objects.filter(event=event).count(), no_screencaptures)

        # When viewed, like it's viewed in the picture gallery and gallery
        # select widget, we want the one called "Screencap 1" to appear
        # before the one called "Screencap 2"
        pictures = Picture.objects.all().order_by('event', '-created')
        notes = [x.notes for x in pictures]
        eq_(
            notes,
            ["Screencap %d" % x for x in range(1, no_screencaptures + 1)]
        )

        # Try to do it again and it shouldn't run it again
        # because there are pictures in the gallery already.
        assert len(ffmpeged_urls) == no_screencaptures, len(ffmpeged_urls)
        videoinfo.fetch_screencaptures()
        eq_(len(ffmpeged_urls), no_screencaptures)
        # and still
        eq_(Picture.objects.filter(event=event).count(), no_screencaptures)

    @mock.patch('airmozilla.manage.vidly.urllib2')
    @mock.patch('requests.head')
    @mock.patch('subprocess.Popen')
    def test_fetch_screencapture_set_first_available(
        self, mock_popen, rhead, p_urllib2
    ):
        assert Picture.objects.all().count() == 0, Picture.objects.all()

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
            return Response(
                '',
                200
            )

        rhead.side_effect = mocked_head

        ffmpeged_urls = []

        sample_jpg = self.sample_jpg
        sample_jpg2 = self.sample_jpg2

        def mocked_popen(command, **kwargs):
            url = command[4]
            ffmpeged_urls.append(url)
            destination = command[-1]
            assert os.path.isdir(os.path.dirname(destination))

            class Inner:
                def communicate(self):
                    out = err = ''
                    if 'xyz123' in url:
                        if '01.jpg' in destination:
                            shutil.copyfile(sample_jpg, destination)
                        else:
                            shutil.copyfile(sample_jpg2, destination)
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
        event.duration = 1157
        event.save()

        # Make sure it has a HD VidlySubmission
        VidlySubmission.objects.create(
            event=event,
            url='https://s3.com/asomething.mov',
            tag='xyz123',
            hd=True,
        )
        event.template_environment = {'tag': 'xyz123'}
        event.save()
        videoinfo.fetch_screencapture(event, set_first_available=True)
        assert ffmpeged_urls
        no_screencaptures = settings.SCREENCAPTURES_NO_PICTURES
        pictures = Picture.objects.filter(event=event)
        eq_(pictures.count(), no_screencaptures)
        event = Event.objects.get(id=event.id)
        eq_(event.picture, pictures.order_by('created')[0])

    @mock.patch('airmozilla.manage.vidly.logging')
    @mock.patch('airmozilla.manage.vidly.urllib2')
    @mock.patch('requests.head')
    @mock.patch('subprocess.Popen')
    def test_fetch_screencapture_without_import(
        self, mock_popen, rhead, p_urllib2, p_log
    ):
        """This test is effectively the same as test_fetch_screencapture()
        but with `import_=False` set.
        """
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
            return Response(
                '',
                200
            )

        rhead.side_effect = mocked_head

        ffmpeged_urls = []

        sample_jpg = self.sample_jpg
        sample_jpg2 = self.sample_jpg2

        def mocked_popen(command, **kwargs):
            url = command[4]
            ffmpeged_urls.append(url)
            destination = command[-1]
            assert os.path.isdir(os.path.dirname(destination))

            class Inner:
                def communicate(self):
                    out = err = ''
                    if 'xyz123' in url:
                        # Let's create two jpeg's in that directory
                        if '01.jpg' in destination:
                            shutil.copyfile(sample_jpg, destination)
                        else:
                            shutil.copyfile(sample_jpg2, destination)
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
        event.duration = 1157
        event.template = template
        event.save()

        # Make sure it has a HD VidlySubmission
        VidlySubmission.objects.create(
            event=event,
            url='https://s3.com/asomething.mov',
            tag='xyz123',
            hd=True,
        )
        event.template_environment = {'tag': 'xyz123'}
        event.save()
        videoinfo.fetch_screencaptures(import_=False)
        assert ffmpeged_urls
        eq_(Picture.objects.filter(event=event).count(), 0)

        # there should now be some JPEGs in the dedicated temp directory
        temp_dir = os.path.join(
            tempfile.gettempdir(),
            settings.SCREENCAPTURES_TEMP_DIRECTORY_NAME
        )
        # expect there to be a directory with the event's ID
        directory_name = '%s_%s' % (event.id, event.slug)
        event_temp_dir = os.path.join(temp_dir, directory_name)
        ok_(os.path.isdir(event_temp_dir))
        # there should be X JPEGs in there
        no_screencaptures = settings.SCREENCAPTURES_NO_PICTURES
        eq_(
            sorted(os.listdir(event_temp_dir)),
            ["screencap-%02d.jpg" % x for x in range(1, no_screencaptures + 1)]
        )

    @mock.patch('airmozilla.manage.vidly.logging')
    @mock.patch('airmozilla.manage.vidly.urllib2')
    @mock.patch('requests.head')
    @mock.patch('subprocess.Popen')
    def test_fetch_screencapture_import_immediately(
        self, mock_popen, rhead, p_urllib2, p_log
    ):
        """This test is effectively the same as test_fetch_screencapture()
        but with `import_immediately=True` set.
        """
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
            return Response(
                '',
                200
            )

        rhead.side_effect = mocked_head

        ffmpeged_urls = []

        sample_jpg = self.sample_jpg
        sample_jpg2 = self.sample_jpg2

        def mocked_popen(command, **kwargs):
            url = command[4]
            ffmpeged_urls.append(url)
            destination = command[-1]
            assert os.path.isdir(os.path.dirname(destination))

            class Inner:
                def communicate(self):
                    out = err = ''
                    if 'xyz123' in url:
                        # Let's create two jpeg's in that directory
                        if '01.jpg' in destination:
                            shutil.copyfile(sample_jpg, destination)
                        else:
                            shutil.copyfile(sample_jpg2, destination)
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
        event.duration = 1157
        event.template = template
        event.save()

        # Make sure it has a HD VidlySubmission
        VidlySubmission.objects.create(
            event=event,
            url='https://s3.com/asomething.mov',
            tag='xyz123',
            hd=True,
        )
        event.template_environment = {'tag': 'xyz123'}
        event.save()
        videoinfo.fetch_screencaptures(import_immediately=True)
        assert ffmpeged_urls
        eq_(
            Picture.objects.filter(event=event).count(),
            settings.SCREENCAPTURES_NO_PICTURES
        )

        # there should now be some JPEGs in the dedicated temp directory
        temp_dir = os.path.join(
            tempfile.gettempdir(),
            settings.SCREENCAPTURES_TEMP_DIRECTORY_NAME
        )
        # expect there to be a directory with the event's ID
        directory_name = '%s_%s' % (event.id, event.slug)
        event_temp_dir = os.path.join(temp_dir, directory_name)
        ok_(not os.path.isdir(event_temp_dir))

    def test_import_screencaptures_empty(self):
        """it should be possible to run this at any time, even if
        the dedicated temp directory does not exist yet. """
        assert not Picture.objects.all().count()
        videoinfo.import_screencaptures()
        ok_(not Picture.objects.all().count())

    def test_import_screencaptures(self):
        """it should be possible to run this at any time, even if
        the dedicated temp directory does not exist yet. """
        event = Event.objects.get(title='Test event')
        # First, put some pictures in the temp directory for this event.
        temp_dir = os.path.join(
            tempfile.gettempdir(),
            settings.SCREENCAPTURES_TEMP_DIRECTORY_NAME
        )
        if not os.path.isdir(temp_dir):
            os.mkdir(temp_dir)
        # expect there to be a directory with the event's ID
        directory_name = '%s_%s' % (event.id, event.slug)
        event_temp_dir = os.path.join(temp_dir, directory_name)
        if not os.path.isdir(event_temp_dir):
            os.mkdir(event_temp_dir)

        # sample_jpg = self.sample_jpg
        # sample_jpg2 = self.sample_jpg2
        shutil.copyfile(
            self.sample_jpg,
            os.path.join(event_temp_dir, 'screencap-01.jpg')
        )
        shutil.copyfile(
            self.sample_jpg2,
            os.path.join(event_temp_dir, 'screencap-02.jpg')
        )
        # Also create an empty broken file
        dest = os.path.join(event_temp_dir, 'screencap-03.jpg')
        with open(dest, 'wb') as f:
            f.write('')

        # An extra one that won't get imported because the name isn't
        # matching.
        shutil.copyfile(
            self.sample_jpg2,
            os.path.join(event_temp_dir, 'otherfile.jpg')
        )

        videoinfo.import_screencaptures()

        ok_(not os.path.isdir(event_temp_dir))
        ok_(os.path.isdir(temp_dir))
        eq_(Picture.objects.filter(event=event).count(), 2)
