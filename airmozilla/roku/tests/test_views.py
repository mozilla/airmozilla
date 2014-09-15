import datetime

from django.conf import settings
from django.utils.timezone import utc

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

    def test_categories_feed_live_events(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        url = reverse('roku:categories_feed')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.title not in response.content)

        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        event.start_time = now - datetime.timedelta(seconds=3600)
        event.save()
        assert not event.archive_time
        assert event in Event.objects.live()
        edgecast_hls = Template.objects.create(
            content='something {{ file }}',
            name='EdgeCast hls'
        )
        event.template = edgecast_hls
        event.template_environment = {'file': 'abc123'}
        event.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.title in response.content)

        # but it really has to have that 'file' attribute
        event.template_environment = {'something': 'else'}
        event.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.title not in response.content)

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
        start_time = event.start_time
        start_time = start_time.replace(year=2014)
        start_time = start_time.replace(month=9)
        start_time = start_time.replace(day=13)
        event.start_time = start_time
        event.save()

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
        ok_('%s - Sep 13 2014' % event.title in response.content)

    def test_event_feed_escape_description(self):
        event = Event.objects.get(title='Test event')
        event.description = (
            'Check out <a href="http://peterbe.com">peterbe</a> '
            "and <script>alert('xss')</script> this."
        )
        vidly = Template.objects.create(
            name="Vid.ly Test",
            content="test"
        )
        event.template = vidly
        event.template_environment = {'tag': 'xyz123'}
        event.save()

        self._attach_file(event, self.main_image)
        url = reverse('roku:event_feed', args=(event.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Check out peterbe and' in response.content)
        ok_('alert(&#39;xss&#39;) this' in response.content)
