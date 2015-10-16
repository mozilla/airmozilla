import datetime

from nose.tools import eq_, ok_
import mock

from django.contrib.auth.models import User, Group
from django.conf import settings
from django.utils import timezone
from django.core.urlresolvers import reverse

from airmozilla.base.tests.testbase import Response, DjangoTestCase
from airmozilla.manage.tweeter import (
    send_tweet,
    send_unsent_tweets,
    tweet_new_published_events,
)
from airmozilla.main.models import (
    Event,
    EventTweet,
    Approval,
    Tag,
    Channel,
)


class TweeterTestCase(DjangoTestCase):

    event_base_data = {
        'status': Event.STATUS_SCHEDULED,
        'description': '...',
        'privacy': 'public',
        'location': '1',
        'channels': '1',
        'tags': 'xxx',
        'template': '1',
        'start_time': '2012-3-4 12:00',
        'estimated_duration': '3600',
        'timezone': 'US/Pacific'
    }
    placeholder = 'airmozilla/manage/tests/firefox.png'

    def setUp(self):
        super(TweeterTestCase, self).setUp()
        settings.TWITTER_USERNAME = 'mrtester'
        settings.TWITTER_CONSUMER_SECRET = 'anything'
        settings.TWITTER_CONSUMER_KEY = 'anything'
        settings.TWITTER_ACCESS_TOKEN = 'anything'
        settings.TWITTER_ACCESS_TOKEN_SECRET = 'anything'

        self.user = User.objects.create_superuser('fake', 'fake@f.com', 'fake')
        assert self.client.login(username='fake', password='fake')

    @mock.patch('twython.Twython')
    def test_send_tweet_without_image(self, mocked_twython):
        event = Event.objects.get(title='Test event')
        event_tweet = EventTweet.objects.create(
            event=event,
            text=u'\xa310,000 for a cup of tea? #testing',
        )
        assert not event_tweet.sent_date
        assert not event_tweet.tweet_id

        def mocked_update_status(status):
            eq_(status, event_tweet.text)
            return {'id': '0000000001'}

        mocker = mock.MagicMock()
        mocker.update_status.side_effect = mocked_update_status
        mocked_twython.return_value = mocker

        send_tweet(event_tweet)
        # fetch it again, to assure it got saved
        event_tweet = EventTweet.objects.get(pk=event_tweet.pk)
        ok_(not event_tweet.error)
        ok_(event_tweet.sent_date)
        eq_(event_tweet.tweet_id, '0000000001')

    @mock.patch('twython.Twython')
    def test_send_tweet_with_image(self, mocked_twython):
        event = Event.objects.get(title='Test event')
        with open(self.placeholder) as fp:
            response = self.client.post(
                reverse('manage:event_edit', args=(event.pk,)),
                dict(self.event_base_data,
                     title=event.title,
                     placeholder_img=fp)
            )
            assert response.status_code == 302, response.status_code
        event = Event.objects.get(pk=event.pk)
        assert event.placeholder_img
        event_tweet = EventTweet.objects.create(
            event=event,
            text=u'\xa310,000 for a cup of tea? #testing',
            include_placeholder=True
        )
        assert not event_tweet.sent_date
        assert not event_tweet.tweet_id

        def mocked_update_status(status, media_ids):
            ok_(isinstance(media_ids, int))
            eq_(status, event_tweet.text)
            return {'id': '0000000001'}

        mocker = mock.MagicMock()
        mocker.update_status.side_effect = (
            mocked_update_status
        )

        def mocked_upload_media(media):
            ok_(media.name)
            return {'media_id': 1234567890}

        mocker.upload_media.side_effect = (
            mocked_upload_media
        )
        mocked_twython.return_value = mocker

        send_tweet(event_tweet)
        # fetch it again, to assure it got saved
        event_tweet = EventTweet.objects.get(pk=event_tweet.pk)
        ok_(not event_tweet.error, event_tweet.error)
        ok_(event_tweet.sent_date)
        eq_(event_tweet.tweet_id, '0000000001')

    @mock.patch('twython.Twython')
    def test_send_tweet_with_error(self, mocked_twython):
        event = Event.objects.get(title='Test event')
        event_tweet = EventTweet.objects.create(
            event=event,
            text=u'\xa310,000 for a cup of tea? #testing',
        )
        assert not event_tweet.sent_date
        assert not event_tweet.tweet_id

        def mocked_update_status(status):
            raise NameError('bla')

        mocker = mock.MagicMock()
        mocker.update_status.side_effect = mocked_update_status
        mocked_twython.return_value = mocker

        send_tweet(event_tweet)
        # fetch it again, to assure it got saved
        event_tweet = EventTweet.objects.get(pk=event_tweet.pk)
        ok_(event_tweet.error)
        ok_(event_tweet.sent_date)
        ok_(not event_tweet.tweet_id)

    @mock.patch('twython.Twython')
    def test_send_unsent_tweets_by_send_date(self, mocked_twython):
        event = Event.objects.get(title='Test event')

        now = timezone.now()
        future = now + datetime.timedelta(hours=1)
        past = now - datetime.timedelta(hours=1)

        event_tweet = EventTweet.objects.create(
            event=event,
            text=u'\xa310,000 for a cup of tea? #testing',
            send_date=future,
        )

        sends = []

        def mocked_update_status(status):
            sends.append(status)
            return {'id': '0000000001'}

        mocker = mock.MagicMock()
        mocker.update_status.side_effect = mocked_update_status
        mocked_twython.return_value = mocker

        send_unsent_tweets()
        ok_(not sends)

        event_tweet.send_date = past
        event_tweet.save()

        send_unsent_tweets()
        eq_(len(sends), 1)

        # all it again
        send_unsent_tweets()
        eq_(len(sends), 1)

    @mock.patch('twython.Twython')
    def test_send_unsent_tweets_no_approval_needed(self, mocked_twython):
        event = Event.objects.get(title='Test event')

        now = timezone.now()
        past = now - datetime.timedelta(hours=1)

        EventTweet.objects.create(
            event=event,
            text=u'\xa310,000 for a cup of tea? #testing',
            send_date=past,
        )

        sends = []

        def mocked_update_status(status):
            sends.append(status)
            return {'id': '0000000001'}

        mocker = mock.MagicMock()
        mocker.update_status.side_effect = mocked_update_status
        mocked_twython.return_value = mocker

        send_unsent_tweets()
        eq_(len(sends), 1)

    @mock.patch('twython.Twython')
    def test_send_unsent_tweets(self, mocked_twython):
        event = Event.objects.get(title='Test event')
        assert event in Event.objects.approved()

        now = timezone.now()
        past = now - datetime.timedelta(hours=1)

        event_tweet = EventTweet.objects.create(
            event=event,
            text=u'\xa310,000 for a cup of tea? #testing',
            send_date=past,
        )
        assert not event_tweet.sent_date
        assert not event_tweet.tweet_id

        sends = []

        def mocked_update_status(status):
            sends.append(status)
            return {'id': '0000000001'}

        mocker = mock.MagicMock()
        mocker.update_status.side_effect = mocked_update_status
        mocked_twython.return_value = mocker

        # change so that it needs an approval
        group = Group.objects.create(name='testapprover')
        approval = Approval.objects.create(
            event=event,
            group=group,
        )
        assert event not in Event.objects.approved()
        event_tweet.send_date = past
        event_tweet.save()

        send_unsent_tweets()
        ok_(not sends)

        # but if it gets approved, it gets sent
        approval.approved = True
        approval.save()

        send_unsent_tweets()
        eq_(len(sends), 1)

    @mock.patch('twython.Twython')
    def test_send_unsent_tweets_with_error(self, mocked_twython):
        event = Event.objects.get(title='Test event')
        event_tweet = EventTweet.objects.create(
            event=event,
            text=u'\xa310,000 for a cup of tea? #testing',
        )
        assert not event_tweet.sent_date
        assert not event_tweet.tweet_id

        sends = []

        def mocked_update_status(status):
            sends.append(status)
            if len(sends) < settings.MAX_TWEET_ATTEMPTS:
                raise Exception("Some Error")
            return {'id': '0000000001'}

        mocker = mock.MagicMock()
        mocker.update_status.side_effect = mocked_update_status
        mocked_twython.return_value = mocker

        send_unsent_tweets()

        event_tweet = EventTweet.objects.get(pk=event_tweet.pk)
        eq_(len(sends), 1)
        ok_(event_tweet.error)
        ok_(event_tweet.sent_date)
        ok_(not event_tweet.tweet_id)

        # try again
        send_unsent_tweets()

        event_tweet = EventTweet.objects.get(pk=event_tweet.pk)
        eq_(len(sends), 2)
        ok_(event_tweet.error)
        ok_(event_tweet.sent_date)
        ok_(not event_tweet.tweet_id)

        # third times the charm
        send_unsent_tweets()

        event_tweet = EventTweet.objects.get(pk=event_tweet.pk)
        eq_(len(sends), 3)
        ok_(not event_tweet.error)
        ok_(event_tweet.sent_date)
        ok_(event_tweet.tweet_id)

        # a fourth time and it won't even be attempted
        send_unsent_tweets()

        eq_(len(sends), 3)

    @mock.patch('requests.get')
    def test_tweet_new_published_events(self, rget):

        def mocked_read(url, params):
            return Response({
                u'status_code': 200,
                u'data': {
                    u'url': u'http://mzl.la/1adh2wT',
                    u'hash': u'1adh2wT',
                    u'global_hash': u'1adh2wU',
                    u'long_url': u'https://air.mozilla.org/it-buildout/',
                    u'new_hash': 0
                },
                u'status_txt': u'OK'
            })

        rget.side_effect = mocked_read

        event = Event.objects.get(title='Test event')
        event.tags.add(Tag.objects.create(name='testing'))
        event_tag, = event.tags.all()
        tweet_new_published_events()

        assert not EventTweet.objects.all()
        assert event.privacy == Event.PRIVACY_PUBLIC
        recently = timezone.now()
        event.created = recently
        event.archive_time = recently
        event.save()

        tweet_new_published_events()
        tweet, = EventTweet.objects.all()
        ok_(event.title in tweet.text)
        ok_('http://mzl.la/1adh2wT' in tweet.text)
        ok_(tweet.include_placeholder)
        ok_('#' + event_tag.name in tweet.text)

        # run it again and no new EventTweet should be created
        tweet_new_published_events()
        eq_(EventTweet.objects.count(), 1)

    @mock.patch('requests.get')
    def test_tweet_new_published_events_almost_too_long(self, rget):

        def mocked_read(url, params):
            return Response({
                u'status_code': 200,
                u'data': {
                    u'url': u'http://mzl.la/1adh2wT',
                    u'hash': u'1adh2wT',
                    u'global_hash': u'1adh2wU',
                    u'long_url': u'https://air.mozilla.org/it-buildout/',
                    u'new_hash': 0
                },
                u'status_txt': u'OK'
            })

        rget.side_effect = mocked_read

        event = Event.objects.get(title='Test event')
        recently = timezone.now()
        event.title = 'A Much Longer Test Title'
        event.created = recently
        event.archive_time = recently
        event.save()
        tags = (
            'firefox',
            'Intern Firefox OS',
            'abba',
            'somereallylongwordthatisactuallyatag',
        )
        for tag in tags:
            event.tags.add(Tag.objects.create(name=tag))

        tweet_new_published_events()
        tweet, = EventTweet.objects.all()
        ok_(event.title in tweet.text)
        ok_('http://mzl.la/1adh2wT' in tweet.text)
        ok_(tweet.include_placeholder)
        ok_('#abba' in tweet.text)
        ok_('#firefox' in tweet.text)
        ok_('#InternFirefoxOS' in tweet.text)
        ok_('#somereallylongwordthatisactuallyatag' not in tweet.text)

    def test_tweet_new_published_events_excluded_channel(self):
        event = Event.objects.get(title='Test event')
        event.created = timezone.now()
        event.archive_time = timezone.now()
        event.save()

        event.channels.add(Channel.objects.create(
            name='Normal',
            slug='normal',
        ))
        event.channels.add(Channel.objects.create(
            name='Excluded',
            slug='excluded',
            no_automated_tweets=True,
        ))

        tweet_new_published_events()
        ok_(not EventTweet.objects.all())

    @mock.patch('requests.get')
    def test_tweet_new_published_future_event(self, rget):

        def mocked_read(url, params):
            return Response({
                u'status_code': 200,
                u'data': {
                    u'url': u'http://mzl.la/1adh2wT',
                    u'hash': u'1adh2wT',
                    u'global_hash': u'1adh2wU',
                    u'long_url': u'https://air.mozilla.org/it-buildout/',
                    u'new_hash': 0
                },
                u'status_txt': u'OK'
            })

        rget.side_effect = mocked_read

        future = timezone.now() + datetime.timedelta(days=1)
        event = Event.objects.get(title='Test event')
        event.title = 'A Much Longer Test Title'
        event.created = timezone.now() - datetime.timedelta(days=1)
        event.start_time = future
        event.save()

        tweet_new_published_events()
        tweet, = EventTweet.objects.all()
        ok_(event.title in tweet.text)
        ok_('http://mzl.la/1adh2wT' in tweet.text)
        eq_(tweet.send_date + datetime.timedelta(minutes=30), future)
