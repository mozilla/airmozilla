from django.test import TestCase
from nose.tools import eq_

from airmozilla.main import cloud


class _Tag(object):
    def __init__(self, name, count):
        self.name = name
        self.count = count


class TestCloud(TestCase):

    def test_calculate_cloud(self):
        tags = [_Tag('one', 3), _Tag('two', 15), _Tag('three', 6)]
        tags_sorted = cloud.calculate_cloud(tags)
        eq_([x.font_size for x in tags_sorted], [2, 4, 3])
