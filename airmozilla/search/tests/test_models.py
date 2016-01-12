from django.contrib.auth.models import User

from nose.tools import ok_, eq_

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.search.models import SavedSearch
from airmozilla.main.models import Event, Tag, Channel


class SavedSearchTestCase(DjangoTestCase):

    def test_get_events(self):
        user = User.objects.create(username='bob')
        savedsearch = SavedSearch.objects.create(
            user=user,
            filters={
                'title': {'include': 'firefox'},
                'tags': {'include': [], 'exclude': []},
                'channels': {'include': [], 'exclude': []},
            }
        )
        eq_(savedsearch.get_events().count(), 0)

        event = Event.objects.get(title='Test event')

        savedsearch.filters['title']['include'] = 'EVENT'
        savedsearch.save()
        ok_(event in savedsearch.get_events())

        savedsearch.filters['title']['exclude'] = 'TEST'
        savedsearch.save()
        ok_(event not in savedsearch.get_events())

        tag = Tag.objects.create(name='tag')
        tag2 = Tag.objects.create(name='tag2')
        event.tags.add(tag)
        event.tags.add(tag2)
        savedsearch.filters['title']['include'] = ''
        savedsearch.filters['title']['exclude'] = ''
        savedsearch.filters['tags']['include'] = [tag.id]
        savedsearch.save()
        ok_(event in savedsearch.get_events())

        savedsearch.filters['tags']['exclude'] = [tag2.id]
        savedsearch.save()
        ok_(event not in savedsearch.get_events())

        channel = Channel.objects.create(name='channel', slug='c')
        channel2 = Channel.objects.create(name='channel2', slug='c2')
        event.channels.add(channel)
        event.channels.add(channel2)
        savedsearch.filters['tags']['include'] = []
        savedsearch.filters['tags']['exclude'] = []
        savedsearch.filters['channels']['include'] = [channel.id]
        savedsearch.save()
        ok_(event in savedsearch.get_events())

        savedsearch.filters['channels']['exclude'] = [channel2.id]
        savedsearch.save()
        ok_(event not in savedsearch.get_events())

        assert event.privacy == Event.PRIVACY_PUBLIC
        savedsearch.filters['channels']['include'] = []
        savedsearch.filters['channels']['exclude'] = []
        savedsearch.filters['privacy'] = [Event.PRIVACY_PUBLIC]
        savedsearch.save()
        ok_(event in savedsearch.get_events())

        savedsearch.filters['privacy'] = [Event.PRIVACY_COMPANY]
        savedsearch.save()
        ok_(event not in savedsearch.get_events())
