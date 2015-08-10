from django.contrib.auth.models import User

from nose.tools import ok_

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.starred.models import StarredEvent
from airmozilla.main.models import Event


class StarredEventTestCase(DjangoTestCase):

    def test_basic_save(self):
        event = Event.objects.get(title='Test event')
        user = User.objects.create(
            username='lisa'
        )
        starred_event = StarredEvent.objects.create(
            event=event,
            user=user
        )
        ok_(starred_event.created)
