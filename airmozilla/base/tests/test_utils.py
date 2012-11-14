import time
import datetime
import pytz
from unittest import TestCase
from cStringIO import StringIO
from nose.tools import eq_, ok_
from mock import patch
from airmozilla.base import utils


class TestVidlyTokenize(TestCase):

    @patch('airmozilla.base.utils.logging')
    @patch('airmozilla.base.utils.urllib2')
    def test_secure_token(self, p_urllib2, p_logging):
        def mocked_urlopen(request):
            return StringIO("""
            <?xml version="1.0"?>
            <Response>
              <Message>OK</Message>
              <MessageCode>7.4</MessageCode>
              <Success>
                <MediaShortLink>8r9e0o</MediaShortLink>
                <Token>MXCsxINnVtycv6j02ZVIlS4FcWP</Token>
              </Success>
            </Response>
            """)
        p_urllib2.urlopen = mocked_urlopen
        eq_(utils.vidly_tokenize('xyz123', 60),
            'MXCsxINnVtycv6j02ZVIlS4FcWP')

    @patch('airmozilla.base.utils.logging')
    @patch('airmozilla.base.utils.urllib2')
    def test_not_secure_token(self, p_urllib2, p_logging):
        def mocked_urlopen(request):
            return StringIO("""
            <?xml version="1.0"?>
            <Response>
              <Message>Error</Message>
              <MessageCode>7.5</MessageCode>
              <Errors>
                <Error>
                  <ErrorCode>8.1</ErrorCode>
                  <ErrorName>Short URL is not protected</ErrorName>
                  <Description>bla bla</Description>
                  <Suggestion>ble ble</Suggestion>
                </Error>
              </Errors>
            </Response>
            """)
        p_urllib2.urlopen = mocked_urlopen
        eq_(utils.vidly_tokenize('abc123', 60), '')

        # do it a second time and it should be cached
        def mocked_urlopen_different(request):
            return StringIO("""
            Anything different
            """)
        p_urllib2.urlopen = mocked_urlopen_different
        eq_(utils.vidly_tokenize('abc123', 60), '')

    @patch('airmozilla.base.utils.logging')
    @patch('airmozilla.base.utils.urllib2')
    def test_invalid_response_token(self, p_urllib2, p_logging):
        def mocked_urlopen(request):
            return StringIO("""
            <?xml version="1.0"?>
            <Response>
              <Message>Error</Message>
              <MessageCode>99</MessageCode>
              <Errors>
                <Error>
                  <ErrorCode>0.0</ErrorCode>
                  <ErrorName>Some other error</ErrorName>
                  <Description>bla bla</Description>
                  <Suggestion>ble ble</Suggestion>
                </Error>
              </Errors>
            </Response>
            """)
        p_urllib2.urlopen = mocked_urlopen
        eq_(utils.vidly_tokenize('def123', 60), None)
        p_logging.error.asert_called_with(
            "Unable fetch token for tag 'abc123'"
        )


class TestVidlyAddMedia(TestCase):

    @patch('airmozilla.base.utils.logging')
    @patch('airmozilla.base.utils.urllib2')
    def test_add_media(self, p_urllib2, p_logging):
        def mocked_urlopen(request):
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
            """)
        p_urllib2.urlopen = mocked_urlopen
        shortcode, error = utils.vidly_add_media('http//www.com')
        eq_(shortcode, '8oxv6x')
        ok_(not error)

        # same thing should work with optional extras
        shortcode, error = utils.vidly_add_media(
            'http//www.com',
            email='mail@peterbe.com',
            token_protection=True
        )
        eq_(shortcode, '8oxv6x')
        ok_(not error)

    @patch('airmozilla.base.utils.logging')
    @patch('airmozilla.base.utils.urllib2')
    def test_add_media_failure(self, p_urllib2, p_logging):
        def mocked_urlopen(request):
            # I don't actually know what it would say
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
            """)
        p_urllib2.urlopen = mocked_urlopen
        shortcode, error = utils.vidly_add_media('http//www.com')
        ok_(not shortcode)
        ok_('0.0' in error)


class TestMisc(TestCase):

    def test_unhtml(self):
        input_ = 'A <a href="">FOO</a> BAR'
        eq_(utils.unhtml(input_), 'A FOO BAR')


class _Communicator(object):
    def __init__(self, response):
        self.response = response

    def communicate(self):
        return self.response


class TestEdgecastTokenize(TestCase):

    @patch('airmozilla.base.utils.subprocess')
    def test_edgecast_tokenize(self, p_subprocess):
        def mocked_popen(command, **pipes):
            assert len(command) == 3
            out = '42624d7f743086e6138f'
            if command[2]:
                out += '?' + command[2]
            return _Communicator([out, ''])

        p_subprocess.Popen = mocked_popen
        eq_(utils.edgecast_tokenize(), '42624d7f743086e6138f')
        now = datetime.datetime.utcnow()
        tz = pytz.timezone('America/Los_Angeles')
        now += tz.utcoffset(now)
        now_ts = int(time.mktime(now.timetuple()))
        eq_(utils.edgecast_tokenize(90),
            '42624d7f743086e6138f?ec_expire=%s' % (now_ts + 90))

    @patch('airmozilla.base.utils.subprocess')
    def test_edgecast_tokenize_erroring(self, p_subprocess):
        def mocked_popen(command, **pipes):
            assert len(command) == 3
            return _Communicator(['', 'Not good'])

        p_subprocess.Popen = mocked_popen
        self.assertRaises(utils.EdgecastEncryptionError,
                          utils.edgecast_tokenize)
