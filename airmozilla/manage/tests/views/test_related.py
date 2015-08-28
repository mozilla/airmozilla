from nose.tools import eq_, ok_

from funfactory.urlresolvers import reverse

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
