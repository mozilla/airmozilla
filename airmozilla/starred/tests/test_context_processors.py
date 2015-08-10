from nose.tools import eq_

from django.test.client import RequestFactory
from django.contrib.auth.models import User, AnonymousUser

from airmozilla.main.models import Event
from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.starred.models import StarredEvent
from airmozilla.starred.context_processors import stars


class StarsTestCase(DjangoTestCase):

    def test_stars_anonymous(self):
        request = RequestFactory().get('/some/page/')
        request.user = AnonymousUser()
        result = stars(request)
        eq_(result, {})

    def test_stars_user_empty(self):
        request = RequestFactory().get('/some/page/')
        request.user = User.objects.create(
            username='lisa'
        )
        result = stars(request)
        eq_(result, {'star_ids': ''})

    def test_stars_user_not_empty(self):
        request = RequestFactory().get('/some/page/')
        user = User.objects.create(
            username='lisa'
        )
        request.user = user
        result = stars(request)
        eq_(result, {'star_ids': ''})

        event = Event.objects.get(title='Test event')
        starred_event = StarredEvent.objects.create(
            event=event,
            user=user,
        )
        result = stars(request)
        eq_(result, {'star_ids': str(event.id)})

        # delete the starred event
        starred_event.delete()
        result = stars(request)
        eq_(result, {'star_ids': ''})

    def test_stars_user_delete_event(self):
        request = RequestFactory().get('/some/page/')
        user = User.objects.create(
            username='lisa'
        )
        request.user = user
        event = Event.objects.get(title='Test event')
        StarredEvent.objects.create(
            event=event,
            user=user,
        )
        result = stars(request)
        eq_(result, {'star_ids': str(event.id)})
        event.delete()
        result = stars(request)
        eq_(result, {'star_ids': ''})
