import unittest

from airmozilla.search.split_search import split_search


class Test(unittest.TestCase):

    def shortDescription(self):
        return None

    def test_basic(self):
        """ one free text part, two keywords """
        keywords = ('to', 'from')
        q = "Peter something to:AAa aa from:Foo bar"
        s, params = split_search(q, keywords)
        self.assertEqual(s, 'Peter something')
        self.assertEqual(params, {'to': 'AAa aa', 'from': 'Foo bar'})

    def test_basic_case_insensitive(self):
        """ keywords should match case insensivitely """
        keywords = ('to', 'from')
        q = "something To:Bar From:Foo"
        s, params = split_search(q, keywords)
        self.assertEqual(s, 'something')
        self.assertEqual(params, {'to': 'Bar', 'from': 'Foo'})

    def test_unrecognized_keywords(self):
        """ free text and keywords we don't support """
        keywords = ('something', 'else')
        q = "Free text junk: Aaa aaa foo:bar"
        s, params = split_search(q, keywords)
        self.assertEqual(s, q)
        self.assertEqual(params, {})

    def test_unrecognized_and_recognized_keywords(self):
        """ free text and keywords we don't support """
        keywords = ('something', 'else', 'name')
        q = "Free text junk: something else name: peter"
        s, params = split_search(q, keywords)
        self.assertEqual(s, 'Free text junk: something else')
        self.assertEqual(params, {'name': 'peter'})

    def test_empty_keyword_value(self):
        """ free text and an empty keyword """
        keywords = ('to',)
        q = "Naughty parameter to:"
        s, params = split_search(q, keywords)
        self.assertEqual(s, "Naughty parameter")
        self.assertEqual(params, {'to': ''})

    def test_unicode_string(self):
        """ test with unicode string input """
        keywords = ('from', 'to')
        q = u"\xa1 to:\xa2 from:\xa3"
        s, params = split_search(q, keywords)
        self.assertEqual(s, u'\xa1')
        self.assertEqual(params, {u'to': u'\xa2', u'from': u'\xa3'})

    def test_invalid_keywords(self):
        """Test to pass invalid keywords"""
        keywords = ('to]',)
        q = "Peter something to:AAa aa"
        self.assertRaises(ValueError, split_search, q, keywords)

    def test_with_colon_in_value(self):
        """what if 'tag' is a valid keyword and the value is something
        like 'git:foobar'"""
        keywords = ['tag']
        q = "find this tag: git:foobar"
        s, params = split_search(q, keywords)
        self.assertEqual(s, 'find this')
        self.assertEqual(params, {'tag': 'git:foobar'})

    def test_just_a_keyword(self):
        """searching for a term which is the keyword"""
        # this is a stupidity of a bug I've found
        keywords = ['tag']
        q = "tag"
        s, params = split_search(q, keywords)
        self.assertEqual(s, 'tag')
        self.assertEqual(params, {})
