import os
from unittest import TestCase

from nose.tools import eq_, ok_

from mock import patch

from airmozilla.suggest import utils


_here = os.path.dirname(__file__)
HAS_OPENGRAPH_FILE = os.path.join(_here, 'has_opengraph.html')
NO_OPENGRAPH_FILE = os.path.join(_here, 'no_opengraph.html')


class Response(object):
    def __init__(self, content=None, status_code=200):
        self.content = content
        self.status_code = status_code


class TestOpenGraph(TestCase):

    @patch('requests.get')
    def test_find_open_graph_image_url(self, rget):

        def mocked_get(url, **kwargs):
            if 'goodurl.com' in url:
                return Response(open(HAS_OPENGRAPH_FILE).read())
            elif 'badurl.com' in url:
                return Response(open(NO_OPENGRAPH_FILE).read())
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        result = utils.find_open_graph_image_url('http://goodurl.com')
        eq_(result, 'https://s3.amazonaws.com/makes.org/c14acbcf08dc.png')

        result = utils.find_open_graph_image_url('http://badurl.com')
        eq_(result, None)


class TestEmailValidation(TestCase):

    def test_is_valid_email(self):
        result = utils.is_valid_email('not')
        ok_(not result)
        result = utils.is_valid_email('is@mozilla.com')
        ok_(result)
