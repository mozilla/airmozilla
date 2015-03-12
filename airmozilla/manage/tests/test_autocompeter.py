import datetime
import json

from nose.tools import ok_, eq_, assert_raises
import mock

from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ImproperlyConfigured

from funfactory.urlresolvers import reverse

from airmozilla.main.models import Event, EventHitStats
from airmozilla.manage import autocompeter
from airmozilla.base.tests.testbase import DjangoTestCase


class Response(object):
    def __init__(self, content, status_code=200, headers=None):
        self.content = self.text = content
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return json.loads(self.content)


class TestAutocompeter(DjangoTestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']

    def test_update_without_key(self):
        with self.settings(AUTOCOMPETER_KEY=None):
            # This would simply fail if autocompeter.py wasn't smart
            # enough to notice that the AUTOCOMPETER_KEY was not set.
            autocompeter.update()

    @mock.patch('requests.post')
    def test_basic_update(self, rpost):

        posts = []

        def mocked_post(url, **options):
            assert settings.AUTOCOMPETER_URL in url
            data = json.loads(options['data'])
            posts.append(data)
            return Response(
                'OK',
                201
            )

        rpost.side_effect = mocked_post

        autocompeter.update()
        # nothing should happen because there are no recently modified events
        ok_(not posts)

        event = Event.objects.get(title='Test event')
        event.save()
        autocompeter.update()
        eq_(len(posts), 1)

        # In the posted data should be a thing called 'documents'
        # which is a list of every document.
        assert len(posts[0]['documents']) == 1
        document = posts[0]['documents'][0]
        eq_(document['url'], reverse('main:event', args=(event.slug,)))
        eq_(document['title'], event.title)
        eq_(document['group'], '')
        eq_(document['popularity'], 0)

    @mock.patch('requests.post')
    def test_basic_update_with_popularity(self, rpost):

        posts = []

        def mocked_post(url, **options):
            assert settings.AUTOCOMPETER_URL in url
            data = json.loads(options['data'])
            posts.append(data)
            return Response(
                'OK',
                201
            )

        rpost.side_effect = mocked_post

        event = Event.objects.get(title='Test event')
        # also change to a non-public privacy setting
        event.privacy = Event.PRIVACY_CONTRIBUTORS
        event.save()
        EventHitStats.objects.create(
            event=event,
            total_hits=100
        )
        autocompeter.update()

        document = posts[0]['documents'][0]
        eq_(document['popularity'], 100)
        eq_(document['group'], Event.PRIVACY_CONTRIBUTORS)

    @mock.patch('requests.post')
    def test_basic_update_upcoming_event(self, rpost):

        posts = []

        def mocked_post(url, **options):
            assert settings.AUTOCOMPETER_URL in url
            data = json.loads(options['data'])
            posts.append(data)
            return Response(
                'OK',
                201
            )

        rpost.side_effect = mocked_post

        event = Event.objects.get(title='Test event')
        EventHitStats.objects.create(
            event=event,
            total_hits=100
        )
        autocompeter.update()

        future = timezone.now() + datetime.timedelta(days=1)
        Event.objects.create(
            slug='aaa',
            title='Other',
            start_time=future,
            status=event.status,
        )
        assert Event.objects.approved().count() == 2
        autocompeter.update()
        assert len(posts[0]['documents']) == 1
        document = posts[0]['documents'][0]
        eq_(document['title'], 'Other')
        # picks this up from the median
        eq_(document['popularity'], 100)

    @mock.patch('requests.post')
    def test_basic_update_all(self, rpost):

        posts = []

        def mocked_post(url, **options):
            assert settings.AUTOCOMPETER_URL in url
            data = json.loads(options['data'])
            posts.append(data)
            return Response(
                'OK',
                201
            )

        rpost.side_effect = mocked_post

        autocompeter.update(all=True)

        assert len(posts[0]['documents']) == 1
        document = posts[0]['documents'][0]
        eq_(document['title'], 'Test event')
        eq_(document['popularity'], 0)

    @mock.patch('requests.post')
    def test_basic_update_all_with_popularity(self, rpost):

        posts = []

        def mocked_post(url, **options):
            assert settings.AUTOCOMPETER_URL in url
            data = json.loads(options['data'])
            posts.append(data)
            return Response(
                'OK',
                201
            )

        rpost.side_effect = mocked_post
        EventHitStats.objects.create(
            event=Event.objects.get(title='Test event'),
            total_hits=200
        )

        autocompeter.update(all=True)

        assert len(posts[0]['documents']) == 1
        document = posts[0]['documents'][0]
        eq_(document['title'], 'Test event')
        eq_(document['popularity'], 200)

    @mock.patch('requests.delete')
    @mock.patch('requests.post')
    def test_basic_update_all_with_flush(self, rpost, rdelete):

        posts = []
        deletes = []

        def mocked_post(url, **options):
            assert settings.AUTOCOMPETER_URL in url
            data = json.loads(options['data'])
            posts.append(data)
            return Response(
                'OK',
                201
            )

        rpost.side_effect = mocked_post

        def mocked_delete(url, **options):
            assert settings.AUTOCOMPETER_URL in url
            deletes.append(url)
            return Response(
                'OK',
                204
            )

        rdelete.side_effect = mocked_delete

        autocompeter.update(all=True, flush_first=True)
        ok_(deletes)
        ok_(posts)

    @mock.patch('requests.get')
    def test_stats(self, rget):

        def mocked_get(url, **options):
            return Response(
                json.dumps({'documents': 1}),
                200,
                headers={
                    'content-type': 'application/json'
                }
            )

        rget.side_effect = mocked_get

        result = autocompeter.stats()
        eq_(result, {'documents': 1})

    def test_stats_no_key(self):
        with self.settings(AUTOCOMPETER_KEY=''):
            assert_raises(
                ImproperlyConfigured,
                autocompeter.stats
            )

    @mock.patch('requests.get')
    def test_test(self, rget):

        def mocked_get(url, **options):
            return Response(
                json.dumps({
                    'terms': ['foo'],
                    'results': [
                        ['/url', 'Page'],
                    ]
                }),
                200,
                headers={
                    'content-type': 'application/json'
                }
            )

        rget.side_effect = mocked_get

        result = autocompeter.test('foo')
        eq_(result['terms'], ['foo'])
        eq_(result['results'], [['/url', 'Page']])
