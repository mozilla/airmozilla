from airmozilla.base.tests.testbase import DjangoTestCase, Response
from airmozilla.main.models import Event
from airmozilla.popcorn.models import PopcornEdit

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
        url = reverse('popcorn:event_meta_data')

        response = self.client.get(url, {})
        eq_(response.status_code, 400)
        event.template.name = 'this is a vid.ly video'
        event.template.save()

        event.template_environment = {'tag': 'abc123'}
        event.save()

        response = self.client.get(url, {'slug': event.slug})
        content = json.loads(response.content)

        eq_(response.status_code, 200)
        ok_(content['preview_img'])
        eq_(content['description'], 'sadfasdf')
        eq_(content['title'], event.title)
        eq_(content['video_url'], location)
        eq_(response['Access-Control-Allow-Origin'], '*')

    @mock.patch('requests.head')
    def test_popcorn_data(self, rhead):
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

        url = reverse('popcorn:popcorn_data')

        response = self.client.get(url, {'slug': event.slug})
        # because we're not logged in
        eq_(response.status_code, 302), rhead

        self._login()

        response = self.client.get(url)
        # because there is no slug
        eq_(response.status_code, 400)

        response = self.client.get(url, {'slug': event.slug})
        eq_(response.status_code, 200)

        content = json.loads(response.content)

        ok_(content['metadata'])

    def test_popcorn_data_exists(self):
        event = Event.objects.get(title='Test event')
        event.template.name = 'this is a vid.ly video'
        event.template.save()

        event.template_environment = {'tag': 'abc123'}
        event.save()

        edit = PopcornEdit.objects.create(
            event=event,
            data={'foo': 'bar'},
            status=PopcornEdit.STATUS_SUCCESS
        )

        url = reverse('popcorn:popcorn_data')

        self._login()

        response = self.client.get(url, {'slug': event.slug})
        eq_(response.status_code, 200)

        content = json.loads(response.content)

        eq_(content['data'], edit.data)

    def test_popcorn_editor(self):
        event = Event.objects.get(title='Test event')
        event.template.name = 'this is a vid.ly video'
        event.template.save()

        event.template_environment = {'tag': 'abc123'}
        event.save()

        url = reverse('popcorn:render_editor', args=(event.slug,))

        response = self.client.get(url, {'slug': event.slug})
        eq_(response.status_code, 302)

        event.privacy = Event.PRIVACY_COMPANY
        event.save()

        response = self.client.get(url, {'slug': event.slug})
        eq_(response.status_code, 302)

        self._login()

        response = self.client.get(url, {'slug': event.slug})
        eq_(response.status_code, 200)
