from nose.tools import eq_

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.main.models import Event, Channel
from airmozilla.main.utils import get_event_channels


class TestEventsToChannels(DjangoTestCase):

    def test_basic_case(self):
        event = Event.objects.get(title='Test event')
        # the fixture event belongs to the Main channel
        assert event.channels.all().count() == 1
        events = Event.objects.all()
        assert events.count() == 1

        channels = get_event_channels(events)
        assert len(channels[event]) == 1
        eq_(channels[event], list(event.channels.all()))

        testing = Channel.objects.create(
            name='Testing',
            slug='testing',
            description='<p>Stuff!</p>'
        )
        event.channels.add(testing)

        channels = get_event_channels(events)
        assert len(channels[event]) == 2
        eq_(channels[event], list(event.channels.all()))
