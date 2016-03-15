from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from nose.tools import eq_

from airmozilla.authentication.backend import AirmozillaBrowserIDBackend


class TestBackend(TestCase):

    # def setUp(self):
    #     super(TestViews, self).setUp()

    def shortDescription(self):
        # Stop nose using the test docstring and instead the test method name.
        pass

    def test_getuser_none(self):
        backend = AirmozillaBrowserIDBackend()
        eq_(backend.get_user(0), None)
        eq_(backend.get_user(None), None)

    def test_getuser_known(self):
        backend = AirmozillaBrowserIDBackend()
        user = User.objects.create(
            username='richard',
            last_login=timezone.now(),
        )
        eq_(backend.get_user(user.id), user)
        # a second time and it should be coming from the cache
        eq_(backend.get_user(user.id), user)
        # change the user and it should be reflected
        user.username = 'zandr'
        user.save()
        eq_(backend.get_user(user.id).username, 'zandr')
        # a second time
        eq_(backend.get_user(user.id).username, 'zandr')

    def test_getuser_deleted(self):
        backend = AirmozillaBrowserIDBackend()
        user = User.objects.create(
            username='richard',
            last_login=timezone.now(),
        )
        eq_(backend.get_user(user.id), user)
        # twice
        eq_(backend.get_user(user.id), user)
        user.delete()
        eq_(backend.get_user(user.id), None)
