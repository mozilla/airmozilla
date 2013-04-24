from cStringIO import StringIO
from nose.tools import eq_, ok_
import mock

from django.test import TestCase

from airmozilla.manage import vidly

SAMPLE_XML = (
    '<?xml version="1.0"?>'
    '<Response><Message>Action successful.</Message>'
    '<MessageCode>4.1</MessageCode><Success><Task><UserID>1234</UserID>'
    '<MediaShortLink>abc123</MediaShortLink>'
    '<SourceFile>http://videos.mozilla.org/bla.f4v</SourceFile>'
    '<BatchID>35402</BatchID>'
    '<Status>Finished</Status>'
    '<Private>false</Private>'
    '<PrivateCDN>false</PrivateCDN><Created>2012-08-23 19:30:58</Created>'
    '<Updated>2012-08-23 20:44:22</Updated>'
    '<UserEmail>airmozilla@mozilla.com</UserEmail>'
    '</Task></Success></Response>'
)

SAMPLE_MEDIALIST_XML = (
    '<?xml version="1.0"?>'
    '<Response><Message>OK</Message><MessageCode>7.4</MessageCode><Success>'
    '<Media><MediaShortLink>abc123</MediaShortLink><VanityLink/>'
    '<Notify>vvm@spb-team.com</Notify><Created>2011-12-25 18:45:56</Created>'
    '<Updated>2012-11-28 14:05:07</Updated><Status>Error</Status>'
    '<IsDeleted>false</IsDeleted><IsPrivate>false</IsPrivate>'
    '<IsPrivateCDN>false</IsPrivateCDN><CDN>AWS</CDN></Media>'
    '<Media><MediaShortLink>xyz987</MediaShortLink><VanityLink/>'
    '<Notify>vvm@spb-team.com</Notify><Created>2011-12-25 19:41:05</Created>'
    '<Updated>2012-11-28 14:04:57</Updated><Status>Error</Status>'
    '<IsDeleted>false</IsDeleted><IsPrivate>false</IsPrivate>'
    '<IsPrivateCDN>false</IsPrivateCDN><CDN>AWS</CDN></Media>'
    '</Success></Response>'
)


class TestVidlyTokenize(TestCase):

    @mock.patch('airmozilla.manage.vidly.logging')
    @mock.patch('airmozilla.manage.vidly.urllib2')
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
        eq_(vidly.tokenize('xyz123', 60),
            'MXCsxINnVtycv6j02ZVIlS4FcWP')

    @mock.patch('airmozilla.manage.vidly.logging')
    @mock.patch('airmozilla.manage.vidly.urllib2')
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
        eq_(vidly.tokenize('abc123', 60), '')

        # do it a second time and it should be cached
        def mocked_urlopen_different(request):
            return StringIO("""
            Anything different
            """)
        p_urllib2.urlopen = mocked_urlopen_different
        eq_(vidly.tokenize('abc123', 60), '')

    @mock.patch('airmozilla.manage.vidly.logging')
    @mock.patch('airmozilla.manage.vidly.urllib2')
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
        eq_(vidly.tokenize('def123', 60), None)
        p_logging.error.asert_called_with(
            "Unable fetch token for tag 'abc123'"
        )


class TestVidlyAddMedia(TestCase):

    @mock.patch('airmozilla.manage.vidly.logging')
    @mock.patch('airmozilla.manage.vidly.urllib2')
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
        shortcode, error = vidly.add_media('http//www.com')
        eq_(shortcode, '8oxv6x')
        ok_(not error)

        # same thing should work with optional extras
        shortcode, error = vidly.add_media(
            'http//www.com',
            email='mail@peterbe.com',
            token_protection=True
        )
        eq_(shortcode, '8oxv6x')
        ok_(not error)

    @mock.patch('airmozilla.manage.vidly.logging')
    @mock.patch('airmozilla.manage.vidly.urllib2')
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
        shortcode, error = vidly.add_media('http//www.com')
        ok_(not shortcode)
        ok_('0.0' in error)


class TestVidlyDeleteMedia(TestCase):

    @mock.patch('airmozilla.manage.vidly.logging')
    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_delete_media(self, p_urllib2, p_logging):
        def mocked_urlopen(request):
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
            """)
        p_urllib2.urlopen = mocked_urlopen
        shortcode, error = vidly.delete_media(
            '8oxv6x',
            email='test@example.com'
        )
        eq_(shortcode, '8oxv6x')
        ok_(not error)

    @mock.patch('airmozilla.manage.vidly.logging')
    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_delete_media_failure(self, p_urllib2, p_logging):
        def mocked_urlopen(request):
            # I don't actually know what it would say
            return StringIO("""
            <?xml version="1.0"?>
            <Response>
              <Message>Success</Message>
              <MessageCode>0.0</MessageCode>
              <Errors>
                <Error>
                  <SourceFile>http://www.com</SourceFile>
                  <ErrorCode>1.1</ErrorCode>
                  <Description>ErrorDescriptionK</Description>
                  <Suggestion>ErrorSuggestionK</Suggestion>
                </Error>
              </Errors>
            </Response>
            """)
        p_urllib2.urlopen = mocked_urlopen
        shortcode, error = vidly.delete_media(
            '8oxv6x',
            email='test@example.com'
        )
        ok_(not shortcode)
        ok_('1.1' in error)


class VidlyTestCase(TestCase):

    @mock.patch('urllib2.urlopen')
    def test_query(self, p_urlopen):

        def mocked_urlopen(request):
            return StringIO(SAMPLE_XML.strip())

        p_urlopen.side_effect = mocked_urlopen

        results = vidly.query('abc123')
        ok_('abc123' in results)
        eq_(results['abc123']['Status'], 'Finished')

    @mock.patch('urllib2.urlopen')
    def test_medialist(self, p_urlopen):

        def mocked_urlopen(request):
            return StringIO(SAMPLE_MEDIALIST_XML.strip())

        p_urlopen.side_effect = mocked_urlopen

        results = vidly.medialist('Error')
        ok_(results['abc123'])
        ok_(results['xyz987'])
