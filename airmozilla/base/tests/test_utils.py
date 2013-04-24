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
