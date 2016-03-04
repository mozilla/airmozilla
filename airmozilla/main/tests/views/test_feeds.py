# -*- coding: utf-8 -*-

import re
import os
import datetime

import mock
from nose.tools import eq_, ok_

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.core.files import File
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from airmozilla.main.models import (
    Approval,
    Event,
    Channel,
    Template,
    Tag,
)
from airmozilla.search.models import SavedSearch
from airmozilla.base.tests.testbase import DjangoTestCase


itunes_image_regex = re.compile(
    'itunes:image href="([^\"]+)"'
)


class ThumbnailResult(object):

    def __init__(self, url, width, height):
        self.url = url
        self.width = width
        self.height = height


class TestFeeds(DjangoTestCase):

    def setUp(self):
        super(TestFeeds, self).setUp()
        # Make the fixture event live as of the test.
        event = Event.objects.get(title='Test event')
        event.start_time = timezone.now()
        event.archive_time = None
        event.save()

        self.main_channel = Channel.objects.get(
            slug=settings.DEFAULT_CHANNEL_SLUG
        )

        self.patch_get_thumbnail = mock.patch(
            'airmozilla.main.templatetags.jinja_helpers.get_thumbnail'
        )
        mocked_get_thumbnail = self.patch_get_thumbnail.start()

        def get_thumbnail(image, geometry, **options):
            width, height = [int(x) for x in geometry.split('x')]
            url = '/media/fake.png'
            if settings.MEDIA_URL:
                url = settings.MEDIA_URL + url[1:]
            return ThumbnailResult(
                url,
                width, height
            )

        mocked_get_thumbnail.side_effect = get_thumbnail

    def tearDown(self):
        super(TestFeeds, self).tearDown()
        self.patch_get_thumbnail.stop()

    def test_feed(self):
        delay = datetime.timedelta(days=1)

        event1 = Event.objects.get(title='Test event')
        event1.status = Event.STATUS_SCHEDULED
        event1.start_time -= delay
        event1.archive_time = event1.start_time
        event1.save()
        eq_(Event.objects.archived().approved().count(), 1)
        eq_(Event.objects.archived().count(), 1)

        event = Event.objects.create(
            title='Second test event',
            description='Anything',
            start_time=event1.start_time,
            archive_time=event1.archive_time,
            privacy=Event.PRIVACY_COMPANY,  # Note!
            status=event1.status,
            placeholder_img=event1.placeholder_img,
        )
        event.channels.add(self.main_channel)

        eq_(Event.objects.archived().approved().count(), 2)
        eq_(Event.objects.archived().count(), 2)

        url = reverse('main:feed', args=('public',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)
        ok_('Second test event' not in response.content)

        url = reverse('main:feed')  # public feed
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)
        ok_('Second test event' not in response.content)

        url = reverse('main:feed', args=('company',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)
        ok_('Second test event' in response.content)

    def test_feed_with_NOT_channel(self):
        cache.clear()
        delay = datetime.timedelta(days=1)

        event1 = Event.objects.get(title='Test event')
        event1.status = Event.STATUS_SCHEDULED
        event1.start_time -= delay
        event1.archive_time = event1.start_time
        event1.save()
        eq_(Event.objects.archived().approved().count(), 1)
        eq_(Event.objects.archived().count(), 1)

        event = Event.objects.create(
            title='Second test event',
            description='Anything',
            start_time=event1.start_time,
            archive_time=event1.archive_time,
            privacy=event1.privacy,
            status=event1.status,
            placeholder_img=event1.placeholder_img,
        )
        event.channels.add(self.main_channel)

        eq_(Event.objects.archived().approved().count(), 2)
        eq_(Event.objects.archived().count(), 2)

        url = reverse('main:feed', args=('public',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)
        ok_('Second test event' in response.content)

        channel = Channel.objects.create(
            name='Projects',
            slug='projects',
        )
        event1.channels.add(channel)

        url = reverse('main:not_feed', args=('public', 'xxx'))
        response = self.client.get(url)
        eq_(response.status_code, 404)

        url = reverse('main:not_feed', args=('public', 'projects'))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' not in response.content)
        ok_('Second test event' in response.content)

    def test_feed_non_unique_titles(self):
        event = Event.objects.get(title='Test event')
        assert event.status == Event.STATUS_SCHEDULED
        assert event.privacy == Event.PRIVACY_PUBLIC
        assert event.start_time
        event.title = u'Färjreföx'
        event.archive_time = timezone.now()
        event.save()

        # use a different channel to avoid getting caught in page ccaching
        channel = Channel.objects.create(
            name='Stuff', slug='stuff'
        )
        event.channels.add(channel)
        # create a clone
        other_event = Event.objects.create(
            title=event.title,
            slug='different',
            privacy=event.privacy,
            start_time=event.start_time - datetime.timedelta(days=2),
            archive_time=timezone.now(),
            template_environment=event.template_environment,
            template=event.template,
            status=event.status,
        )
        other_event.channels.add(channel)

        url = reverse('main:channel_feed_default', args=('stuff',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        assert response.content.count('<item>') == 2
        title_regex = re.compile('<title>(.*?)</title>')
        _, item_title1, item_title2 = title_regex.findall(response.content)
        # Because they're non-unique they should have been separated
        # with the events' `get_unique_title()` method.
        ok_(item_title1 != item_title2)

    def test_feed_unapproved_events(self):
        event = Event.objects.get(title='Test event')
        assert event.is_public()
        assert event in Event.objects.live()
        assert event in Event.objects.live().approved()

        public_url = reverse('main:feed', args=('public',))
        private_url = reverse('main:feed', args=('private',))

        response = self.client.get(public_url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)
        response = self.client.get(public_url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)

        cache.clear()

        app = Approval.objects.create(event=event)
        response = self.client.get(public_url)
        eq_(response.status_code, 200)
        ok_('Test event' not in response.content)
        response = self.client.get(private_url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)

        app.processed = True
        app.save()
        response = self.client.get(public_url)
        eq_(response.status_code, 200)
        ok_('Test event' not in response.content)
        response = self.client.get(private_url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)

        cache.clear()

        app.approved = True
        app.save()
        response = self.client.get(public_url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)
        response = self.client.get(private_url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)

    def test_feed_with_webm_format(self):
        delay = datetime.timedelta(days=1)

        event1 = Event.objects.get(title='Test event')
        event1.status = Event.STATUS_SCHEDULED
        event1.start_time -= delay
        event1.archive_time = event1.start_time
        vidly_template = Template.objects.create(
            name='Vid.ly Something',
            content='<script>'
        )
        event1.template = vidly_template
        event1.template_environment = {'tag': 'abc123'}
        event1.save()
        eq_(Event.objects.approved().count(), 1)
        eq_(Event.objects.archived().count(), 1)

        url = reverse('main:feed_format_type', args=('public', 'webm'))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(
            '<link>https://vid.ly/abc123?content=video&amp;format=webm</link>'
            in response.content
        )

    def test_feed_with_savedsearch(self):
        url = reverse('main:feed')
        response = self.client.get(url)
        ok_('Test event' in response.content)

        savedsearch = SavedSearch.objects.create(
            user=User.objects.create(username='richard'),
            filters={
                'title': {
                    'include': 'FLY'
                }
            }
        )

        response = self.client.get(url, {'ss': savedsearch.id})
        ok_('Test event' not in response.content)
        event = Event.objects.get(title='Test event')
        event.title = 'Flying to the Moon'
        event.save()
        response = self.client.get(url, {'ss': savedsearch.id})
        ok_('Flying to the Moon' not in response.content)
        # because the feed is cached
        cache.clear()
        response = self.client.get(url, {'ss': savedsearch.id})
        ok_('Flying to the Moon' in response.content)

    def test_feed_cache(self):
        delay = datetime.timedelta(days=1)

        event = Event.objects.get(title='Test event')
        event.start_time -= delay
        event.archive_time = event.start_time
        event.save()

        url = reverse('main:feed')
        eq_(Event.objects.archived().approved().count(), 1)
        eq_(Event.objects.archived().count(), 1)
        response = self.client.get(url)
        ok_('Test event' in response.content)

        event.title = 'Totally different'
        event.save()

        response = self.client.get(url)
        ok_('Test event' in response.content)
        ok_('Totally different' not in response.content)

    def test_private_feeds_by_channel(self):
        channel = Channel.objects.create(
            name='Culture and Context',
            slug='culture-and-context',
        )
        delay = datetime.timedelta(days=1)

        event1 = Event.objects.get(title='Test event')
        event1.status = Event.STATUS_SCHEDULED
        event1.start_time -= delay
        event1.archive_time = event1.start_time
        event1.save()
        event1.channels.clear()
        event1.channels.add(channel)

        eq_(Event.objects.archived().approved().count(), 1)
        eq_(Event.objects.archived().count(), 1)

        event = Event.objects.create(
            title='Second test event',
            description='Anything',
            start_time=event1.start_time,
            archive_time=event1.archive_time,
            privacy=Event.PRIVACY_COMPANY,  # Note!
            status=event1.status,
            placeholder_img=event1.placeholder_img,
        )
        event.channels.add(channel)

        eq_(Event.objects.archived().approved().count(), 2)
        eq_(Event.objects.archived().count(), 2)
        eq_(Event.objects.filter(channels=channel).count(), 2)

        url = reverse(
            'main:channel_feed',
            args=('culture-and-context', 'public')
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)
        ok_('Second test event' not in response.content)

        # public feed
        url = reverse(
            'main:channel_feed_default',
            args=('culture-and-context',)
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)
        ok_('Second test event' not in response.content)

        url = reverse(
            'main:channel_feed',
            args=('culture-and-context', 'company')
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Test event' in response.content)
        ok_('Second test event' in response.content)

    def test_feeds_by_channel_with_webm_format(self):
        channel = Channel.objects.create(
            name='Culture and Context',
            slug='culture-and-context',
        )
        delay = datetime.timedelta(days=1)

        event1 = Event.objects.get(title='Test event')
        event1.status = Event.STATUS_SCHEDULED
        event1.start_time -= delay
        event1.archive_time = event1.start_time
        vidly_template = Template.objects.create(
            name='Vid.ly Something',
            content='<script>'
        )
        event1.template = vidly_template
        event1.template_environment = {'tag': 'abc123'}
        event1.save()
        event1.channels.clear()
        event1.channels.add(channel)

        event = Event.objects.create(
            title='Second test event',
            description='Anything',
            start_time=event1.start_time,
            archive_time=event1.archive_time,
            privacy=Event.PRIVACY_PUBLIC,
            status=event1.status,
            placeholder_img=event1.placeholder_img,
        )

        event.channels.add(channel)

        eq_(Event.objects.approved().count(), 2)
        eq_(Event.objects.archived().count(), 2)
        eq_(Event.objects.filter(channels=channel).count(), 2)

        url = reverse(
            'main:channel_feed_format_type',
            args=('culture-and-context', 'public', 'webm')
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        assert 'Second test event' in response.content
        ok_(
            '<link>https://vid.ly/abc123?content=video&amp;format=webm</link>'
            in response.content
        )

    def test_itunes_feed(self):
        url = reverse('main:itunes_feed')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # expect no items in it...
        assert '<item>' not in response.content
        # but we can check some important itunes tags
        ok_('<itunes:explicit>clean</itunes:explicit>' in response.content)
        ok_(
            '<itunes:category text="Technology"></itunes:category>'
            in response.content
        )
        ok_('<title>Air Mozilla' in response.content)
        ok_('<language>en-US</language>' in response.content)
        ok_('<itunes:subtitle>' in response.content)
        ok_('<itunes:summary>' in response.content)
        ok_('<itunes:email>' in response.content)
        ok_('<itunes:name>' in response.content)
        ok_('<itunes:image href="http' in response.content)

    def test_itunes_with_custom_channel_cover_art(self):
        channel = Channel.objects.get(slug=settings.DEFAULT_CHANNEL_SLUG)
        with open(self.main_image, 'rb') as f:
            img = File(f)
            channel.cover_art.save(os.path.basename(self.main_image), img)

        url = reverse('main:itunes_feed')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('podcast-cover-1400x1400.png' not in response.content)

        with self.settings(MEDIA_URL='//somecdn.example/'):
            response = self.client.get(url)
            eq_(response.status_code, 200)
            href = itunes_image_regex.findall(response.content)[0]
            eq_(href, 'http://somecdn.example/media/fake.png')

    def test_itunes_feed_custom_channel(self):
        url = reverse('main:itunes_feed', args=('rUsT',))
        response = self.client.get(url)
        eq_(response.status_code, 404)

        Channel.objects.create(name='Rust', slug='rust')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('<title>Air Mozilla' not in response.content)
        ok_('<title>Rust on Air Mozilla' in response.content)

    @mock.patch('airmozilla.main.models.get_video_redirect_info')
    def test_itunes_feed_item(self, r_get_redirect_info):

        def mocked_get_redirect_info(tag, format_, hd=False, expires=60):
            return {
                'url': 'http://cdn.vidly/file.mp4',
                'type': 'video/mp4',
                'length': '1234567',
            }

        r_get_redirect_info.side_effect = mocked_get_redirect_info

        event = Event.objects.get(title='Test event')
        event.archive_time = timezone.now()
        event.template_environment = {'tag': 'abc123'}
        event.duration = 60 * 60 + 60 + 1
        event.short_description = 'Short "description"'
        event.description = 'Long <a href="http://www.peterbe.com">URL</a>'
        event.save()
        event.template.name = 'Vid.ly something'
        event.template.save()
        event.tags.add(Tag.objects.create(name='Tag1'))
        event.tags.add(Tag.objects.create(name='Tag2'))
        assert event in Event.objects.archived().approved().filter(
            privacy=Event.PRIVACY_PUBLIC,
            template__name__icontains='Vid.ly',
        )
        url = reverse('main:itunes_feed')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        assert '<item>' in response.content
        xml_ = response.content.split('<item>')[1].split('</item>')[0]
        ok_(event.title in xml_)
        ok_(event.short_description in xml_)
        ok_(
            event.description.replace('<', '&lt;').replace('>', '&gt;') in xml_
        )
        ok_('<itunes:duration>01:01:01</itunes:duration>' in xml_)
        ok_('<itunes:keywords>Tag1,Tag2</itunes:keywords>' in xml_)

    @mock.patch('airmozilla.main.models.get_video_redirect_info')
    def test_itunes_feed_from_sub_channel(self, r_get_redirect_info):

        def mocked_get_redirect_info(tag, format_, hd=False, expires=60):
            return {
                'url': 'http://cdn.vidly/file.mp4',
                'type': 'video/mp4',
                'length': '1234567',
            }

        r_get_redirect_info.side_effect = mocked_get_redirect_info

        event = Event.objects.get(title='Test event')
        event.archive_time = timezone.now()
        event.template_environment = {'tag': 'abc123'}
        event.duration = 60
        event.save()
        event.template.name = 'Vid.ly something'
        event.template.save()
        assert event in Event.objects.archived()
        main_channel = Channel.objects.get(slug=settings.DEFAULT_CHANNEL_SLUG)
        event.channels.remove(main_channel)
        parent_channel = Channel.objects.create(name='Events', slug='events')
        sub_channel = Channel.objects.create(
            name='Rust',
            slug='rust',
            parent=parent_channel,
        )
        event.channels.add(sub_channel)

        url = reverse('main:itunes_feed', args=('events',))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        assert '<item>' in response.content
        xml_ = response.content.split('<item>')[1].split('</item>')[0]
        ok_(event.title in xml_)

    @mock.patch('airmozilla.main.models.get_video_redirect_info')
    def test_itunes_feed_with_repeated_titles(self, r_get_redirect_info):

        def mocked_get_redirect_info(tag, format_, hd=False, expires=60):
            return {
                'url': 'http://cdn.vidly/file.mp4',
                'type': 'video/mp4',
                'length': '1234567',
            }

        r_get_redirect_info.side_effect = mocked_get_redirect_info

        event = Event.objects.get(title='Test event')
        event.title = u'Nånting på svenska'
        event.save()
        event.archive_time = timezone.now()
        event.template_environment = {'tag': 'abc123'}
        event.duration = 60
        event.save()
        event.template.name = 'Vid.ly something'
        event.template.save()
        assert event in Event.objects.archived()
        assert event.channels.filter(slug=settings.DEFAULT_CHANNEL_SLUG)

        # now create a clone with the same title
        other_event = Event.objects.create(
            title=event.title,
            slug='other',
            start_time=event.start_time - datetime.timedelta(days=2),
            archive_time=timezone.now(),
            template_environment=event.template_environment,
            template=event.template,
            privacy=event.privacy,
            status=event.status,
            duration=event.duration,
        )
        for channel in event.channels.all():
            other_event.channels.add(channel)
        assert other_event in Event.objects.archived()

        url = reverse('main:itunes_feed')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        assert response.content.count('<item>') == 2
        title_regex = re.compile('<title>(.*?)</title>')
        _, item_title1, item_title2 = title_regex.findall(response.content)
        # Because they're non-unique they should have been separated
        # with the events' `get_unique_title()` method.
        ok_(item_title1 != item_title2)
