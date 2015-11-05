import urllib
from cStringIO import StringIO

from nose.tools import eq_, ok_, assert_raises
import mock

from airmozilla.base.tests.testbase import DjangoTestCase, Response
from airmozilla.main.models import Event, VidlySubmission
from airmozilla.manage import vidly


def get_custom_XML(**kwargs):
    return (
        '<?xml version="1.0"?>'
        '<Response><Message>{message}</Message>'
        '<MessageCode>{message_code}</MessageCode>'
        '<Success><Task><UserID>{user_id}</UserID>'
        '<MediaShortLink>{tag}</MediaShortLink>'
        '<SourceFile>{source_file}</SourceFile>'
        '<BatchID>{batch_id}</BatchID>'
        '<Status>{status}</Status>'
        '<Private>{private}</Private>'
        '<PrivateCDN>{private_cdn}</PrivateCDN>'
        '<IsHD>{hd}</IsHD>'
        '<Created>{created}</Created>'
        '<Updated>{updated}</Updated>'
        '<UserEmail>{user_email}</UserEmail>'
        '</Task></Success></Response>'
    ).format(message=kwargs.get('message', 'Action successful.'),
             message_code=kwargs.get('message_code', '4.1'),
             user_id=kwargs.get('user_id', '1234'),
             tag=kwargs.get('tag', 'abc123').encode('utf8'),
             source_file=kwargs.get(
                 'source_file', 'http://videos.mozilla.org/bla.f4v'),
             batch_id=kwargs.get('batch_id', '35402'),
             status=kwargs.get('status', 'Finished'),
             private=kwargs.get('private', 'false'),
             private_cdn=kwargs.get('private_cdn', 'false'),
             hd=kwargs.get('hd', 'false'),
             created=kwargs.get('created', '2012-08-23 19:30:58'),
             updated=kwargs.get('updated', '2012-08-23 20:44:22'),
             user_email=kwargs.get('user_email', 'airmozilla@mozilla.com'))


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
    '<Duration>350.75</Duration>'
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


SAMPLE_STATISTICS_XML = (
    '<?xml version="1.0"?>'
    '<Response><Message/><MessageCode/><Success><StatsInfo><StatsTable>'
    '<cols><col>Class</col><col>Vendor</col><col>Model</col>'
    '<col>Platform</col><col>OS</col><col>Browser</col><col>Browser Ver</col>'
    '<col>Hits</col></cols><rows><row><col>Desktop</col><col></col><col></col>'
    '<col></col><col>Apple</col><col>Firefox</col><col>21.0</col><col>5</col>'
    '</row><row><col>Desktop</col><col></col><col></col><col></col>'
    '<col>Apple</col><col>Firefox</col><col>20.0</col><col>2</col></row>'
    '</rows></StatsTable><Others>0</Others><TotalHits>10</TotalHits>'
    '</StatsInfo></Success></Response>'
)

SAMPLE_STATISTICS_BROKEN_XML = (
    '<?xml version="1.0"?>'
    '<Response><Message/><MessageCode/><Success><StatsInfo>'
    '</StatsInfo></Success></Response>'
)


SAMPLE_INVALID_LINKS_XML = (
    '<?xml version="1.0"?>'
    '<Response><Message>Action failed: all media short links are wrong.'
    '</Message><MessageCode>4.3</MessageCode><Errors><Error>'
    '<ErrorCode>4.1</ErrorCode>'
    '<ErrorName>No media short links provided.</ErrorName>'
    '<Description>You have not provided any media short links in your request '
    'or all media short links are invalid.</Description><Suggestion>Check '
    'that you have provided valid media short links in your request. If you '
    'have used batch ID, verify that it contains any media links (you may '
    'need to consult site administrator for this).</Suggestion></Error>'
    '</Errors></Response>'
)

SAMPLE_MEDIA_UPDATED_XML = (
    '<?xml version="1.0"?>'
    '<Response><Message>All medias have been updated.</Message>'
    '<MessageCode>2.5</MessageCode>'
    '</Response>'
)

SAMPLE_MEDIA_UPDATE_FAILED_XML = (
    '<?xml version="1.0"?>'
    '<Response>'
    '<Message>Action failed: none of media short link were updated.</Message>'
    '<MessageCode>2.6</MessageCode>'
    '<Errors>'
    '<Error>'
    '<ErrorCode>8.4</ErrorCode>'
    '<ErrorName>Media invalidation in progress</ErrorName>'
    '<Description>Media invalidation in progress</Description>'
    '<Suggestion></Suggestion>'
    '<SourceFile>9b8a4b</SourceFile>'
    '</Error>'
    '</Errors>'
    '</Response>'
)


class TestVidlyTokenize(DjangoTestCase):

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_secure_token(self, p_urllib2):

        event = Event.objects.get(title='Test event')
        submission = VidlySubmission.objects.create(
            event=event,
            tag='xyz123'
        )

        tokenize_calls = []  # globally scope mutable

        def mocked_urlopen(request):
            tokenize_calls.append(1)
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
        eq_(
            vidly.tokenize(submission.tag, 60),
            'MXCsxINnVtycv6j02ZVIlS4FcWP'
        )
        eq_(len(tokenize_calls), 1)
        # do it a second time
        eq_(
            vidly.tokenize(submission.tag, 60),
            'MXCsxINnVtycv6j02ZVIlS4FcWP'
        )
        eq_(len(tokenize_calls), 1)  # caching for the win!

        submission.token_protection = True
        submission.save()

        eq_(
            vidly.tokenize(submission.tag, 60),
            'MXCsxINnVtycv6j02ZVIlS4FcWP'
        )
        eq_(len(tokenize_calls), 2)  # cache got invalidated

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


class TestVidlyAddMedia(DjangoTestCase):

    @mock.patch('airmozilla.manage.vidly.logging')
    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_add_media_with_email(self, p_urllib2, p_logging):
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
    def test_add_media_with_notify_url(self, p_urllib2, p_logging):
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

        def mocked_Request(url, query_string):
            ok_(
                '<Notify>https://mywebhook.example.com</Notify>' in
                urllib.unquote(query_string)
            )
            return mock.MagicMock()

        p_urllib2.Request = mocked_Request
        p_urllib2.urlopen = mocked_urlopen
        shortcode, error = vidly.add_media(
            'http//www.com',
            notify_url='https://mywebhook.example.com',
        )
        eq_(shortcode, '8oxv6x')
        ok_(not error)

    def test_add_media_with_notify_url_and_email(self):
        assert_raises(
            TypeError,
            vidly.add_media,
            'http://example.com',
            email='peterbe@example.com',
            notify_url='http://example.com/hook',
        )

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


class TestVidlyDeleteMedia(DjangoTestCase):

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


class VidlyTestCase(DjangoTestCase):

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

    @mock.patch('urllib2.urlopen')
    def test_statistics(self, p_urlopen):

        def mocked_urlopen(request):
            return StringIO(SAMPLE_STATISTICS_XML.strip())

        p_urlopen.side_effect = mocked_urlopen

        results = vidly.statistics('abc123')
        eq_(results['total_hits'], 10)

    @mock.patch('urllib2.urlopen')
    def test_statistics_broken(self, p_urlopen):

        def mocked_urlopen(request):
            return StringIO(SAMPLE_STATISTICS_BROKEN_XML.strip())

        p_urlopen.side_effect = mocked_urlopen

        results = vidly.statistics('abc123')
        eq_(results, None)

    @mock.patch('urllib2.urlopen')
    def test_update_media_protection_protect(self, p_urlopen):

        def mocked_urlopen(request):
            xml_string = urllib.unquote_plus(request.data)
            ok_('<Protect><Token /></Protect>' in xml_string)
            return StringIO(SAMPLE_MEDIA_UPDATED_XML.strip())

        p_urlopen.side_effect = mocked_urlopen

        # This doesn't return anything but we're only interested in if it
        # can execute at all without errors.
        vidly.update_media_protection('abc123', True)

    @mock.patch('urllib2.urlopen')
    def test_update_media_protection_unprotect(self, p_urlopen):

        def mocked_urlopen(request):
            xml_string = urllib.unquote_plus(request.data)
            ok_('<Protect />' in xml_string)
            return StringIO(SAMPLE_MEDIA_UPDATED_XML.strip())

        p_urlopen.side_effect = mocked_urlopen

        # This doesn't return anything but we're only interested in if it
        # can execute at all without errors.
        vidly.update_media_protection('abc123', False)

    @mock.patch('urllib2.urlopen')
    def test_update_media_protection_error(self, p_urlopen):

        def mocked_urlopen(request):
            return StringIO(SAMPLE_MEDIA_UPDATE_FAILED_XML.strip())

        p_urlopen.side_effect = mocked_urlopen

        # This doesn't return anything but we're only interested in if it
        # can execute at all without errors.
        assert_raises(
            vidly.VidlyUpdateError,
            vidly.update_media_protection,
            'abc123', True
        )

    @mock.patch('requests.head')
    def test_get_video_redirect_info(self, rhead):

        head_requests = []

        def mocked_head(url):
            head_requests.append(url)
            if url == 'http://cdn.vidly/file.mp4':
                return Response('', 302, headers={
                    'Content-Type': 'video/mp5',
                    'Content-Length': '1234567',
                })
            else:
                return Response('', 302, headers={
                    'Location': 'http://cdn.vidly/file.mp4',
                })

        rhead.side_effect = mocked_head

        data = vidly.get_video_redirect_info('abc123', 'mp4', hd=True)
        eq_(data, {
            'url': 'http://cdn.vidly/file.mp4',
            'length': 1234567L,
            'type': 'video/mp5',
        })

    @mock.patch('requests.head')
    def test_get_video_redirect_info_not_found(self, rhead):

        head_requests = []

        def mocked_head(url):
            head_requests.append(url)
            return Response('Not found', 404)

        rhead.side_effect = mocked_head

        assert_raises(
            vidly.VidlyNotFoundError,
            vidly.get_video_redirect_info,
            'xyz123',
            'mp4',
            hd=True
        )
