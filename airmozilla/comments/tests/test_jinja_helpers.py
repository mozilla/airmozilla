from nose.tools import eq_, ok_

from django.test import TestCase

from airmozilla.comments.templatetags.jinja_helpers import (
    gravatar_src,
    obscure_email,
)


class TestHelpers(TestCase):

    def test_gravatar_src_http(self):
        email = 'peterbe@mozilla.com'
        result = gravatar_src(email, False)
        ok_(result.startswith('//www.gravatar.com'))
        # case insensitive
        eq_(result, gravatar_src(email.upper(), False))

    def test_gravatar_src_with_size(self):
        result = gravatar_src('peterbe@mozilla.com', False, size=50)
        ok_(result.startswith('//www.gravatar.com'))
        ok_('s=50' in result)
        eq_(result.count('?'), 1)

    def test_gravatar_src_https(self):
        email = 'peterbe@mozilla.com'
        result = gravatar_src(email, True)
        ok_(result.startswith('//secure.gravatar.com'))

    def test_obscure_email(self):
        email = 'peterbe@mozilla.com'
        result = obscure_email(email)
        eq_(result, 'pete...@...illa.com')
