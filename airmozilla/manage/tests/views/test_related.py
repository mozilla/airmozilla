from nose.tools import eq_, ok_

from django.conf import settings
from django.core.urlresolvers import reverse

from airmozilla.main.models import Event, Tag
from airmozilla.manage import related
from .base import ManageTestCase


class TestRelatedContent(ManageTestCase):

    def setUp(self):
        super(TestRelatedContent, self).setUp()

        es = related.get_connection()
        related.delete(es)
        related.create(es)
        index = related.get_index()
        es.health(
            index=index,
            wait_for_status='yellow',
            wait_for_relocating_shards=0,  # wait for all
            timeout='5m'
        )

    def test_see_related_content(self):
        url = reverse('manage:related_content')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('<b>0 documents</b> indexed' in response.content)
        ok_('<b>1 events</b> (scheduled or processing)' in response.content)

        # start an indexing
        response = self.client.post(url, {'all': True})
        eq_(response.status_code, 302)
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('<b>1 documents</b> indexed' in response.content)

        response = self.client.post(url, {'since': 5})  # last 5 min
        eq_(response.status_code, 302)
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('<b>1 documents</b> indexed' in response.content)

        # now clear and start over
        response = self.client.post(url, {'delete_and_recreate': True})
        eq_(response.status_code, 302)
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('<b>1 documents</b> indexed' in response.content)

    def test_related_content_testing(self):
        url = reverse('manage:related_content_testing')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('<h4>Matches</h4>' not in response.content)
        ok_(str(settings.RELATED_CONTENT_BOOST_TITLE) in response.content)
        ok_(str(settings.RELATED_CONTENT_BOOST_TAGS) in response.content)

        response = self.client.get(url, {
            'event': 'notfound',
            'boost_title': settings.RELATED_CONTENT_BOOST_TITLE,
            'boost_tags': settings.RELATED_CONTENT_BOOST_TAGS,
            'use_title': True,
            'use_tags': True,
        })
        eq_(response.status_code, 200)
        ok_('<h4>Matches</h4>' not in response.content)

        response = self.client.get(url, {
            'event': 'notfound',
            'boost_title': settings.RELATED_CONTENT_BOOST_TITLE,
            'boost_tags': settings.RELATED_CONTENT_BOOST_TAGS,
            'use_title': True,
            'use_tags': True,
        })
        eq_(response.status_code, 200)
        ok_('<h4>Matches</h4>' not in response.content)

        # create another event to be found
        event = Event.objects.get(title='Test event')
        other = Event.objects.create(
            title='Peterbe Testing',
            slug='also',
            privacy=event.privacy,
            status=event.status,
            start_time=event.start_time,
        )
        assert other in Event.objects.scheduled_or_processing()
        tag = Tag.objects.create(name='Swimming')
        other.tags.add(tag)
        event.tags.add(tag)

        related_content_url = reverse('manage:related_content')
        response = self.client.post(
            related_content_url, {'delete_and_recreate': True}
        )
        eq_(response.status_code, 302)
        response = self.client.get(related_content_url)
        eq_(response.status_code, 200)
        ok_('<b>2 documents</b> indexed' in response.content)

        response = self.client.get(url, {
            'event': event.title.upper(),
            'boost_title': settings.RELATED_CONTENT_BOOST_TITLE,
            'boost_tags': settings.RELATED_CONTENT_BOOST_TAGS,
            'size': settings.RELATED_CONTENT_SIZE,
            'use_title': True,
            'use_tags': True,
        })
        eq_(response.status_code, 200)
        ok_('<h4>Matches</h4>' in response.content)
        ok_('Peterbe' in response.content)

        response = self.client.get(url, {
            'event': event.title.upper(),
            'boost_title': settings.RELATED_CONTENT_BOOST_TITLE,
            'boost_tags': settings.RELATED_CONTENT_BOOST_TAGS,
            'size': settings.RELATED_CONTENT_SIZE,
            'use_title': False,
            'use_tags': False,
        })
        eq_(response.status_code, 200)
        ok_('<h4>Matches</h4>' not in response.content)
