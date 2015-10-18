import datetime

from django.conf import settings
from django.utils import timezone
from django.core.files import File
from django.core.urlresolvers import reverse

from nose.tools import eq_, ok_

from airmozilla.main.models import (
    Event,
    Channel,
    Template,
    Picture,
    EventHitStats,
    Approval,
)
from airmozilla.base.tests.testbase import DjangoTestCase


class TestRoku(DjangoTestCase):
    """These tests are deliberately very UN-thorough.
    That's because this whole app is very much an experiment.
    """

    def test_categories_feed(self):
        url = reverse('roku:categories_feed')
        main_channel = Channel.objects.get(slug=settings.DEFAULT_CHANNEL_SLUG)
        main_url = reverse('roku:channel_feed', args=(main_channel.slug,))
        trending_url = reverse('roku:trending_feed')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(main_url in response.content)
        ok_(trending_url in response.content)

    def test_categories_feed_live_events(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        url = reverse('roku:categories_feed')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.title not in response.content)

        now = timezone.now()
        event.start_time = now - datetime.timedelta(seconds=3600)
        event.archive_time = None
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

        # if the *needs* approval, it shouldn't appear
        app = Approval.objects.create(event=event)
        response = self.client.get(main_url)
        eq_(response.status_code, 200)
        ok_(event.title not in response.content)

        app.processed = True
        app.save()
        response = self.client.get(main_url)
        eq_(response.status_code, 200)
        ok_(event.title not in response.content)

        app.approved = True
        app.save()
        response = self.client.get(main_url)
        eq_(response.status_code, 200)
        ok_(event.title in response.content)

    def test_channel_feed_with_no_placeholder(self):
        main_channel = Channel.objects.get(slug=settings.DEFAULT_CHANNEL_SLUG)
        main_url = reverse('roku:channel_feed', args=(main_channel.slug,))
        event = Event.objects.get(title='Test event')

        with open(self.main_image) as fp:
            picture = Picture.objects.create(file=File(fp))

        vidly = Template.objects.create(
            name="Vid.ly Test",
            content="test"
        )
        event.picture = picture
        event.placeholder_img = None
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

    def test_event_duration(self):
        event = Event.objects.get(title='Test event')
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
        ok_('<runtime>3600</runtime>' in response.content)

        event.duration = 12
        event.save()

        self._attach_file(event, self.main_image)
        url = reverse('roku:event_feed', args=(event.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('<runtime>12</runtime>' in response.content)

    def test_trending_feed(self):
        url = reverse('roku:trending_feed')
        response = self.client.get(url)
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
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # because it's not trending
        ok_(event.title not in response.content)

        EventHitStats.objects.create(
            event=event,
            total_hits=1000,
        )
        # This save will trigger to disrupt the cache used inside
        # get_featured_events() since it'll change the modified time.
        event.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.title in response.content)
