from django.contrib.auth.models import Group, User, Permission
from django.conf import settings
from django.test import TestCase

from airmozilla.manage import related

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
    main_image = 'airmozilla/manage/tests/firefox.png'

    def setUp(self):
        super(RelatedTestCase, self).setUp()
        related.flush()

    def test_related_content_logged(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        # make another event which is similar
        other = Event.objects.create(
            title='Event test',
            description='bla bla',
            status=event.status,
            start_time=event.start_time,
            archive_time=event.archive_time,
            privacy=event.privacy,
            placeholder_img=event.placeholder_img,
            )
        # for i in range(10):
        #     Event.objects.create(
        #         title='Event testing %s' %i,
        #         description='bla bla',
        #         status=event.status,
        #         start_time=event.start_time,
        #         archive_time=event.archive_time,
        #         privacy=event.privacy,
        #         )
        tag1 = Tag.objects.create(name='SomeTag')
        other.tags.add(tag1)
        event.tags.add(tag1)
        related.index(all=True)
        # es=related.get_connection()
        # idx = settings.ELASTICSEARCH_PREFIX + settings.ELASTICSEARCH_INDEX
        # mlt_query = {
        #     'more_like_this' : {
        #         'fields' : ['title',],
        #         'docs' : [
        #         {
        #             '_index' : idx,
        #             '_type' : 'event',
        #             '_id' : str(event.id)
        #         }],
        #         'min_term_freq': 1,
        #         'min_term_freq' : 1,
        #         'max_query_terms' : 12
        #     }
        # }
        # print "SEARCH!!!"
        # query = {'query': mlt_query, 'from': 0, 'size': 10}
        # print es.search(query, index=idx)
        # from time import sleep
        # sleep(2)

        self._login()

        url = reverse('main:related_content', args=(event.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Event test' in response.content)
        print response.content

    # def test_unrelated(self):
    #     event = Event.objects.get(title='Test event')
    #     # make another event which is dissimilar
    #     other2 = Event.objects.create(
    #         title='Mozilla Festival',
    #         description='party time',
    #         status=event.status,
    #         start_time=event.start_time,
    #         archive_time=event.archive_time,
    #         privacy=Event.PRIVACY_PUBLIC,
    #         )
    #
    #     tag2 = Tag.objects.create(name='PartyTag')
    #     other2.tags.add(tag2)
    #
    #     index()
    #     ok_('Mozilla Festival' not in response.content)
    #
    # def test_related_event_private(self):
    #     from airmozilla.main.views import is_contributor
    #     # more things to be added
