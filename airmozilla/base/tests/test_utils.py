import json
import time
import datetime
import pytz
from unittest import TestCase
from nose.tools import eq_
from mock import patch
from airmozilla.base import utils


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


class TestBitlyURLShortener(TestCase):

    @patch('urllib.urlopen')
    def test_url_shortener_ok(self, p_urlopen):

        def mocked_read():
            r = {
                u'status_code': 200,
                u'data': {
                    u'url': u'http://mzl.la/1adh2wT',
                    u'hash': u'1adh2wT',
                    u'global_hash': u'1adh2wU',
                    u'long_url': u'https://air.mozilla.org/it-buildout/',
                    u'new_hash': 0
                },
                u'status_txt': u'OK'
            }
            return json.dumps(r)

        p_urlopen().read.side_effect = mocked_read
        url = 'https://air.mozilla.org/something/'
        short = utils.shorten_url(url)
        eq_(short, 'http://mzl.la/1adh2wT')

    @patch('urllib.urlopen')
    def test_url_shortener_error(self, p_urlopen):

        def mocked_read():
            r = {
                u'status_code': 500,
                u'data': [],
                u'status_txt': u'INVALID_URI'
            }
            return json.dumps(r)

        p_urlopen().read.side_effect = mocked_read
        url = 'https://air.mozilla.org/something/'
        self.assertRaises(ValueError, utils.shorten_url, url)


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
