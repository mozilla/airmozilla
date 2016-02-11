import datetime

from nose.tools import eq_, ok_

from django.contrib.auth.models import User, AnonymousUser
from django.test import TestCase
from django.test.client import RequestFactory
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from django.core.urlresolvers import reverse

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.main.models import (
    Event,
    UserProfile,
    Channel,
    EventHitStats,
)
from airmozilla.uploads.models import Upload
from airmozilla.main.context_processors import (
    browserid,
    autocompeter,
    nav_bar,
    get_featured_events,
)


class TestBrowserID(TestCase):

    def test_redirect_next(self):
        request = RequestFactory().get('/some/page/')
        result = browserid(request)['redirect_next']()
        eq_(result, '/some/page/')

        request = RequestFactory().get('/some/page/?next=/other/page/')
        result = browserid(request)['redirect_next']()
        eq_(result, '/other/page/')

    def test_redirect_next_exceptions(self):
        request = RequestFactory().get(reverse('main:login'))
        result = browserid(request)['redirect_next']()
        eq_(result, '/')

        request = RequestFactory().get(reverse('main:login_failure'))
        result = browserid(request)['redirect_next']()
        eq_(result, '/')

    def test_redirect_invalid_next(self):
        next = 'http://www.peterbe.com'
        request = RequestFactory().get('/some/page/?next=%s' % next)
        result = browserid(request)['redirect_next']()
        eq_(result, '/')


class TestAutocompeter(TestCase):

    def setUp(self):
        super(TestAutocompeter, self).setUp()
        settings.AUTOCOMPETER_KEY = 'somethingrandomlooking'

    def test_autocompeter_disabled(self):
        request = RequestFactory().get('/')
        request.user = AnonymousUser()
        with self.settings(AUTOCOMPETER_KEY=None):
            result = autocompeter(request)
            eq_(result, {})

    def test_autocompeter_anonymous(self):
        request = RequestFactory().get('/')
        request.user = AnonymousUser()
        result = autocompeter(request)
        eq_(result['autocompeter_groups'], '')

    def test_autocompeter_employee(self):
        request = RequestFactory().get('/')
        request.user = User.objects.create(
            username='employee'
        )
        result = autocompeter(request)
        eq_(
            result['autocompeter_groups'],
            '%s,%s' % (Event.PRIVACY_CONTRIBUTORS, Event.PRIVACY_COMPANY)
        )

    def test_autocompeter_contributor(self):
        request = RequestFactory().get('/')
        request.user = User.objects.create(
            username='contributor'
        )
        UserProfile.objects.create(
            user=request.user,
            contributor=True,
        )
        result = autocompeter(request)
        eq_(
            result['autocompeter_groups'],
            '%s' % (Event.PRIVACY_CONTRIBUTORS,)
        )

    def test_autocompeter_different_domain(self):
        request = RequestFactory().get('/')
        request.user = AnonymousUser()
        result = autocompeter(request)
        eq_(result['autocompeter_domain'], '')
        with self.settings(AUTOCOMPETER_DOMAIN='airmo'):
            result = autocompeter(request)
            eq_(result['autocompeter_domain'], 'airmo')

    def test_autocompeter_different_url(self):
        request = RequestFactory().get('/')
        request.user = AnonymousUser()
        result = autocompeter(request)
        # this has a default in tests
        eq_(result['autocompeter_url'], settings.AUTOCOMPETER_URL)
        with self.settings(AUTOCOMPETER_URL='http://autocompeter.dev/v1'):
            result = autocompeter(request)
            eq_(result['autocompeter_url'], 'http://autocompeter.dev/v1')


class TestNavBar(TestCase):

    def test_anonymous(self):
        request = RequestFactory().get('/')
        request.user = AnonymousUser()
        data = nav_bar(request)['nav_bar']()
        urls = [x[1] for x in data['items']]
        assert len(urls) == 5, len(urls)
        ok_('/' in urls)
        ok_('/about/' in urls)
        ok_(reverse('main:channels') in urls)
        ok_(reverse('main:calendar') in urls)
        ok_(reverse('main:tag_cloud') in urls)

    def test_signed_in_contributor(self):
        request = RequestFactory().get('/')
        request.user = User.objects.create(
            username='contributor'
        )
        UserProfile.objects.create(
            user=request.user,
            contributor=True,
        )
        data = nav_bar(request)['nav_bar']()
        urls = [x[1] for x in data['items']]
        all_sub_items = [x[-1] for x in data['items']]

        ok_('/' in urls)
        ok_('/about/' in urls)
        ok_(reverse('main:channels') in urls)
        ok_(reverse('main:calendar') in urls)
        ok_(reverse('main:tag_cloud') in urls)
        # ok_(reverse('starred:home') in urls)
        ok_(reverse('new:home') in urls)
        # under the second to last (new)
        sub_items = all_sub_items[-2]
        urls = [x[1] for x in sub_items]
        assert len(urls) == 4
        ok_(reverse('new:home') + 'record' in urls)
        ok_(reverse('new:home') + 'upload' in urls)
        ok_(reverse('new:home') + 'youtube' in urls)
        ok_(reverse('suggest:start') + '#new' in urls)
        # under the last (you) there should be some personal links too
        sub_items = all_sub_items[-1]
        urls = [x[1] for x in sub_items]
        assert len(urls) == 3
        ok_(reverse('starred:home') in urls)
        ok_(reverse('search:savedsearches') in urls)
        ok_(reverse('manage:events') not in urls)
        ok_('/browserid/logout/' in urls)

    def test_signed_in_staff(self):
        request = RequestFactory().get('/')
        request.user = User.objects.create(
            username='richard',
            is_staff=True
        )
        data = nav_bar(request)['nav_bar']()
        all_sub_items = [x[-1] for x in data['items']]
        # urls = [x[1] for x in data['items']]
        sub_items = all_sub_items[-1]
        urls = [x[1] for x in sub_items]
        ok_(reverse('manage:events') in urls)

    def test_signed_in_with_unfinished_events(self):
        request = RequestFactory().get('/')
        request.user = User.objects.create(
            username='richard',
        )
        event = Event.objects.create(
            creator=request.user,
            status=Event.STATUS_INITIATED,
            start_time=timezone.now(),
        )
        upload = Upload.objects.create(
            user=request.user,
            url='https://aws.example.com/file.mov',
            size=123,
            mime_type='video/quicktime',
            event=event
        )
        event.upload = upload
        event.save()

        data = nav_bar(request)['nav_bar']()
        all_sub_items = [x[-1] for x in data['items']]
        # sub_items = all_sub_items[-1]
        # urls = [x[1] for x in sub_items]
        # under the second to last (new)
        sub_items = all_sub_items[-2]
        assert len(sub_items) == 5, len(sub_items)
        first = sub_items[0]
        eq_(first[0], 'Unfinished Videos (1)')
        eq_(first[1], reverse('new:home'))


class TestFeatured(DjangoTestCase):

    def test_get_featured_events(self):
        channels = Channel.objects.filter(
            slug=settings.DEFAULT_CHANNEL_SLUG
        )
        user = User.objects.create(
            username='richard',
        )
        events = get_featured_events(channels, user)
        eq_(events, [])

        event = Event.objects.get(title='Test event')
        # must be archived some time ago
        yesterday = timezone.now() - datetime.timedelta(days=1)
        assert event.archive_time < yesterday
        # must be scheduled
        assert event.status == Event.STATUS_SCHEDULED
        # must be in the main channel
        assert event.channels.filter(slug=settings.DEFAULT_CHANNEL_SLUG)
        # must have some hits
        EventHitStats.objects.create(
            event=event,
            total_hits=100,
            shortcode='abc123'
        )
        # finally!
        events = get_featured_events(channels, user)
        # because it's cacjed
        eq_(events, [])
        # however...
        cache.clear()
        events = get_featured_events(channels, user)
        eq_(events, [event])

        # should work even if the event is processing
        event.status = Event.STATUS_PROCESSING
        event.save()
        cache.clear()
        events = get_featured_events(channels, user)
        eq_(events, [event])

        # but not if it's removed
        event.status = Event.STATUS_REMOVED
        event.save()
        cache.clear()
        events = get_featured_events(channels, user)
        eq_(events, [])
