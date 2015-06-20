from airmozilla.base.tests.testbase import DjangoTestCase, Response
from airmozilla.main.models import Event

import mock
import json

from nose.tools import eq_, ok_

from funfactory.urlresolvers import reverse


class TestPopcornEvent(DjangoTestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']
    main_image = 'airmozilla/manage/tests/firefox.png'

    def setUp(self):
        super(TestPopcornEvent, self).setUp()

        # The event we're going to clone needs to have a real image
        # associated with it so it can be rendered.
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)

    @mock.patch('requests.head')
    def test_meta_data_api(self, rhead):
        location = 'http://localhost'

        def mocked_head(url, **options):
            return Response(
                '',
                302,
                headers={
                    'location': location
                }
            )

        rhead.side_effect = mocked_head

        event = Event.objects.get(title='Test event')
        event.template.name = 'this is a vid.ly video'
        event.template.save()

        event.template_environment = {'tag': 'abc123'}
        event.save()

        url = reverse('popcorn:event_meta_data')

        response = self.client.get(url, {'slug': event.slug})
        content = json.loads(response.content)

        eq_(response.status_code, 200)
        ok_(content['preview_img'])
        eq_(content['description'], 'sadfasdf')
        eq_(content['title'], event.title)
        eq_(content['video_url'], location)
        eq_(response['Access-Control-Allow-Origin'], '*')
