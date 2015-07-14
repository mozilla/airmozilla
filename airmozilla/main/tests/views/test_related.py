from django.contrib.auth.models import Group, User, Permission
from django.conf import settings
from django.test import TestCase

from airmozilla.manage.related import index

from nose.tools import eq_, ok_
from funfactory.urlresolvers import reverse
from airmozilla.main.models import (
    Event,
    Tag,
    Channel,
    EventOldSlug,
)

from airmozilla.base.tests.testbase import DjangoTestCase


class RelatedTestCase(DjangoTestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']

    def test_related_content(self):
        event = Event.objects.get(title='Test event')
        # make another event which is similar
        other = Event.objects.create(
            title='Event testing',
            description='bla bla',
            status=event.status,
            start_time=event.start_time,
            archive_time=event.archive_time,
            privacy=event.privacy,
            )

        print other.title
        tag1 = Tag.objects.create(name='SomeTag')
        other.tags.add(tag1)
        event.tags.add(tag1)
        index(event)

        url = reverse('main:related_content', args=(event.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Event testing' in response.content)

    def test_unrelated(self):
        event = Event.objects.get(title='Test event')
        # make another event which is dissimilar
        other2 = Event.objects.create(
            title='Mozilla Festival',
            description='party time',
            status=event.status,
            start_time=event.start_time,
            archive_time=event.archive_time,
            privacy=Event.PRIVACY_PUBLIC,
            )

        tag2 = Tag.objects.create(name='PartyTag')
        other2.tags.add(tag2)

        index()
        ok_('Mozilla Festival' not in response.content)

    def test_related_event_private(self):
        from airmozilla.main.views import is_contributor
        # more things to be added
