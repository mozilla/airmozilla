from django.conf import settings

from funfactory.urlresolvers import reverse
from nose.tools import eq_, ok_

from airmozilla.main.models import Event, Channel, Template
from airmozilla.base.tests.testbase import DjangoTestCase


class TestRoku(DjangoTestCase):
    """These tests are deliberately very UN-thorough.
    That's because this whole app is very much an experiment.
    """
    fixtures = ['airmozilla/manage/tests/main_testdata.json']
    main_image = 'airmozilla/manage/tests/firefox.png'

    def test_categories_feed(self):
        url = reverse('roku:categories_feed')
        main_channel = Channel.objects.get(slug=settings.DEFAULT_CHANNEL_SLUG)
        main_url = reverse('roku:channel_feed', args=(main_channel.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(main_url in response.content)

    def test_channel_feed(self):
        main_channel = Channel.objects.get(slug=settings.DEFAULT_CHANNEL_SLUG)
        main_url = reverse('roku:channel_feed', args=(main_channel.slug,))
        response = self.client.get(main_url)
        eq_(response.status_code, 200)
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        ok_(event.title not in response.content)

        vidly = Template.objects.create(
            name="Vid.ly Test",
            content="test"
        )
        event.template = vidly
        event.template_environment = {'tag': 'xyz123'}
        event.save()
        response = self.client.get(main_url)
        eq_(response.status_code, 200)
        ok_(event.title in response.content)

    def test_event_feed(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        url = reverse('roku:event_feed', args=(event.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        event = Event.objects.get(title='Test event')
        ok_(event.title not in response.content)

        vidly = Template.objects.create(
            name="Vid.ly Test",
            content="test"
        )
        event.template = vidly
        event.template_environment = {'tag': 'xyz123'}
        event.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.title in response.content)
