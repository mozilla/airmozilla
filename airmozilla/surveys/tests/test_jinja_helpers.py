from nose.tools import eq_

from django.test import TestCase

from airmozilla.surveys.templatetags.jinja_helpers import max_


class TestHelpers(TestCase):

    def test_max_(self):
        eq_(max_(1, 2), 2)
