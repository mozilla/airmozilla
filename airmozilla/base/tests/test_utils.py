import time
import datetime
import pytz
from unittest import TestCase

from nose.tools import eq_, ok_, assert_raises
from mock import patch

from django.test.client import RequestFactory

from airmozilla.base import utils
from airmozilla.base.tests.testbase import DjangoTestCase, Response


class TestMisc(DjangoTestCase):

    def test_unhtml(self):
        input_ = 'A <a href="">FOO</a> BAR'
        eq_(utils.unhtml(input_), 'A FOO BAR')

    def test_prepare_vidly_video_url(self):
        url = 'https://foo.bar/file.flv'
        eq_(utils.prepare_vidly_video_url(url), url)

        url = 'https://mybucket.s3.amazonaws.com/file.mp4'
        eq_(utils.prepare_vidly_video_url(url), url + '?nocopy')

        url = 'https://mybucket.s3.amazonaws.com/file.mp4?cachebust=1'
        eq_(utils.prepare_vidly_video_url(url), url + '&nocopy')

    def test_get_base_url(self):
        request = RequestFactory().get('/')
        root_url = utils.get_base_url(request)
        eq_(root_url, 'http://testserver')

        request = RequestFactory().get('/', SERVER_PORT=443)
        request.is_secure = lambda: True
        assert request.is_secure()
        root_url = utils.get_base_url(request)
        eq_(root_url, 'https://testserver')

    def test_get_abs_static(self):
        rq = RequestFactory().get('/')
        absolute_relative_path = self._create_static_file('foo.png', 'data')
        url = utils.get_abs_static('foo.png', rq)
        eq_(url, 'http://testserver%s' % absolute_relative_path)

    def test_roughly(self):
        numbers = []
        for i in range(100):
            numbers.append(utils.roughly(100, 10))
        # expect at least one of them to be less than 100
        ok_([x for x in numbers if x < 100])
        # same the other way
        ok_([x for x in numbers if x > 100])
        ok_(min(numbers) >= 90)
        ok_(max(numbers) <= 110)


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
        token = utils.edgecast_tokenize(90)
        expected_token = '42624d7f743086e6138f?ec_expire=%s' % (now_ts + 90)
        eq_(token[:-2], expected_token[:-2])

    @patch('airmozilla.base.utils.subprocess')
    def test_edgecast_tokenize_erroring(self, p_subprocess):
        def mocked_popen(command, **pipes):
            assert len(command) == 3
            return _Communicator(['', 'Not good'])

        p_subprocess.Popen = mocked_popen
        assert_raises(utils.EdgecastEncryptionError, utils.edgecast_tokenize)


class TestAkamaiTokenize(TestCase):

    def test_akamai_tokenize(self):
        key = 'a0b378a82fd2521125fb849f'
        token = utils.akamai_tokenize(key=key)
        ok_(token)
        # the default token_name is 'hdnea'
        ok_(token.startswith('hdnea='))
        new_token = utils.akamai_tokenize(key=key)
        # window is too small for it to change
        eq_(new_token, token)
        different_token = utils.akamai_tokenize(key=key[::-1])
        ok_(token != different_token)
        assert_raises(
            TypeError,
            utils.akamai_tokenize,
            key='wrong length'
        )


class TestBitlyURLShortener(TestCase):

    @patch('requests.get')
    def test_url_shortener_ok(self, rget):

        def mocked_read(url, params):
            return Response({
                u'status_code': 200,
                u'data': {
                    u'url': u'http://mzl.la/1adh2wT',
                    u'hash': u'1adh2wT',
                    u'global_hash': u'1adh2wU',
                    u'long_url': u'https://air.mozilla.org/it-buildout/',
                    u'new_hash': 0
                },
                u'status_txt': u'OK'
            })

        rget.side_effect = mocked_read
        url = 'https://air.mozilla.org/something/'
        short = utils.shorten_url(url)
        eq_(short, 'http://mzl.la/1adh2wT')

    @patch('requests.get')
    def test_url_shortener_error(self, rget):

        def mocked_read(url, params):
            return Response({
                u'status_code': 500,
                u'data': [],
                u'status_txt': u'INVALID_URI'
            })

        rget.side_effect = mocked_read
        url = 'https://air.mozilla.org/something/'
        assert_raises(ValueError, utils.shorten_url, url)


class TestDotDict(TestCase):

    def test_basic_use(self):
        data = {
            'type': 'Info',
            'meta': {
                'name': 'Peter'
            }
        }
        dotted = utils.dot_dict(data)
        eq_(dotted.type, 'Info')
        eq_(dotted.meta.name, 'Peter')
