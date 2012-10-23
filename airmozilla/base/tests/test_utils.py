from unittest import TestCase
from cStringIO import StringIO
from nose.tools import eq_
from mock import patch
from airmozilla.base import utils


class TestVidlyTokenize(TestCase):

    @patch('airmozilla.base.utils.logging')
    @patch('airmozilla.base.utils.urllib2')
    def test_secure_token(self, p_urlib2, p_logging):
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
        p_urlib2.urlopen = mocked_urlopen
        eq_(utils.vidly_tokenize('xyz123', 60),
            'MXCsxINnVtycv6j02ZVIlS4FcWP')

    @patch('airmozilla.base.utils.logging')
    @patch('airmozilla.base.utils.urllib2')
    def test_not_secure_token(self, p_urlib2, p_logging):
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
        p_urlib2.urlopen = mocked_urlopen
        eq_(utils.vidly_tokenize('abc123', 60), '')

        # do it a second time and it should be cached
        def mocked_urlopen_different(request):
            return StringIO("""
            Anything different
            """)
        p_urlib2.urlopen = mocked_urlopen_different
        eq_(utils.vidly_tokenize('abc123', 60), '')

    @patch('airmozilla.base.utils.logging')
    @patch('airmozilla.base.utils.urllib2')
    def test_invalid_response_token(self, p_urlib2, p_logging):
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
        p_urlib2.urlopen = mocked_urlopen
        eq_(utils.vidly_tokenize('def123', 60), None)
        p_logging.error.asert_called_with(
            "Unable fetch token for tag 'abc123'"
        )
