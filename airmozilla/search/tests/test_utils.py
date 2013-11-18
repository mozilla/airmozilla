import unittest

from nose.tools import eq_, ok_

from airmozilla.search import utils


class TestUtils(unittest.TestCase):

    def test_possible_to_or_query(self):
        function = utils.possible_to_or_query

        # too short
        ok_(not function('peter'))

        # too short if exclude short words
        ok_(not function('peter X'))

        # too short if exclude stop words
        ok_(not function('peter this'))

        # normal and should work
        ok_(function('peter bengtsson'))

        # but can't contain special characters
        ok_(not function('peter | bengtsson'))
        ok_(not function('peter & bengtsson'))

    def test_make_q_query(self):
        function = utils.make_or_query

        eq_(function('peter'), 'peter')

        eq_(function('peter bengtsson'), 'peter|bengtsson')

        # stopwords are filtered out
        eq_(function('peter this'), 'peter')
