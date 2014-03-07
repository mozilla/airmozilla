import datetime
from nose.tools import eq_
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils.timezone import utc

from funfactory.urlresolvers import reverse

from airmozilla.suggest.helpers import (
    next_url,
    state_description,
    truncate_url
)
from airmozilla.main.models import SuggestedEvent, Event, Location, Participant


class TestStateHelpers(TestCase):

    def setUp(self):
        self.user = User.objects.create_user('nigel', 'n@live.in', 'secret')
        self.participant = Participant.objects.create(
            name='Bill Gates',
            cleared=Participant.CLEARED_SUGGESTED,
        )

    def test_get_getting_state(self):
        event = SuggestedEvent.objects.create(
            user=self.user,
            title='Cheese!',
            slug='cheese'
        )
        url = next_url(event)
        eq_(url, reverse('suggest:description', args=(event.pk,)))
        description = state_description(event)
        eq_(description, 'Description not entered')

        event.description = 'Some description'
        event.save()
        url = next_url(event)
        eq_(url, reverse('suggest:details', args=(event.pk,)))
        description = state_description(event)
        eq_(description, 'Details missing')

        event.start_time = datetime.datetime.utcnow().replace(tzinfo=utc)
        event.location = Location.objects.create(
            name='Mountain View', timezone='US/Pacific',
        )
        event.privacy = Event.PRIVACY_PUBLIC
        event.save()
        url = next_url(event)
        eq_(url, reverse('suggest:placeholder', args=(event.pk,)))
        description = state_description(event)
        eq_(description, 'No placeholder image')

        event.placeholder_img = 'some/path.png'
        event.save()
        url = next_url(event)
        #eq_(url, reverse('suggest:participants', args=(event.pk,)))
        #description = state_description(event)
        #eq_(description, 'No participants selected')
        #event.participants.add(self.participant)
        #url = next_url(event)
        eq_(url, reverse('suggest:summary', args=(event.pk,)))
        description = state_description(event)
        eq_(description, 'Not yet submitted')

        event.submitted = datetime.datetime.utcnow().replace(tzinfo=utc)
        event.save()
        url = next_url(event)
        eq_(url, reverse('suggest:summary', args=(event.pk,)))
        description = state_description(event)
        eq_(description, 'Submitted')


class TestTruncateURL(TestCase):

    def test_truncate_short(self):
        url = 'http://www.peterbe.com'
        result = truncate_url(url, 30)
        eq_(result, url)
        assert len(result) <= 30

    def test_truncate_long(self):
        url = 'http://www.peterbe.com'
        result = truncate_url(url, 20)
        expect = url[:10] + u'\u2026' + url[-10:]
        eq_(result, expect)
