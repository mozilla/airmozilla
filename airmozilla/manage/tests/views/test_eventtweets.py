import datetime
import json

from nose.tools import eq_, ok_
import mock

from django.conf import settings
from django.contrib.auth.models import Group
from django.utils import timezone
from django.core.urlresolvers import reverse

from airmozilla.main.models import (
    Event,
    EventTweet,
    Location,
    Approval
)
from .base import ManageTestCase
from airmozilla.base.tests.test_utils import Response


class TestEventTweets(ManageTestCase):

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

    @mock.patch('requests.get')
    def test_prepare_new_tweet(self, rget):

        def mocked_read(url, params):
            assert url == settings.BITLY_URL
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
        # the event must have a real placeholder image
        with open(self.placeholder) as fp:
            response = self.client.post(
                reverse('manage:event_edit', args=(event.pk,)),
                dict(self.event_base_data,
                     title=event.title,
                     short_description="Check out <b>This!</b>",
                     description="Something longer",
                     placeholder_img=fp)
            )
            assert response.status_code == 302, response.status_code

        # on the edit page, there should be a link
        response = self.client.get(
            reverse('manage:event_edit', args=(event.pk,))
        )
        assert response.status_code == 200
        url = reverse('manage:new_event_tweet', args=(event.pk,))
        ok_(url in response.content)

        response = self.client.get(url)
        eq_(response.status_code, 200)
        textarea = (
            response.content
            .split('<textarea')[1]
            .split('>')[1]
            .split('</textarea')[0]
        )
        ok_(textarea.strip().startswith('Check out This!'))
        event = Event.objects.get(pk=event.pk)
        event_url = 'http://testserver'
        event_url += reverse('main:event', args=(event.slug,))
        ok_('http://mzl.la/1adh2wT' in textarea)
        ok_(event_url not in textarea)

        # Sometimes, due to...
        # https://bugzilla.mozilla.org/show_bug.cgi?id=1167211
        # the session is cleared out here in this test, so we
        # really make sure we're signed in
        assert self.client.login(username='fake', password='fake')
        assert self.client.session.items()

        # load the form
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # try to submit it with longer than 140 characters
        response = self.client.post(url, {
            'text': 'x' * 141,
            'include_placeholder': True,
        })
        eq_(response.status_code, 200)
        assert not EventTweet.objects.all().count()
        ok_('it has 141' in response.content)

        # try again
        response = self.client.post(url, {
            'text': 'Bla bla #tag',
            'include_placeholder': True,
        })
        eq_(response.status_code, 302)
        ok_(EventTweet.objects.all().count())
        now = timezone.now()
        event_tweet, = EventTweet.objects.all()
        # To avoid being unlucky about the second ticking over
        # just before we compare these, make it OK to be up to 2 seconds
        # apart.
        diff = abs(event_tweet.send_date - now)
        ok_(diff < datetime.timedelta(seconds=2))
        ok_(not event_tweet.sent_date)
        ok_(not event_tweet.error)
        ok_(not event_tweet.tweet_id)

    @mock.patch('requests.get')
    def test_prepare_new_tweet_on_future_event(self, rget):

        def mocked_read(url, params):
            assert url == settings.BITLY_URL
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
        event.start_time = timezone.now() + datetime.timedelta(days=10)
        event.save()
        assert event.is_scheduled()
        assert event.location
        assert event.location.timezone

        # on the edit page, there should be a link
        url = reverse('manage:new_event_tweet', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        help_text_part = 'This event starts %s' % (
            event.location_time.strftime('%Y-%m-%d %H:%M')
        )
        ok_(help_text_part in response.content)

    def test_edit_event_tweet(self):
        event = Event.objects.get(title='Test event')
        assert event.location and event.location.timezone == 'US/Pacific'
        tomorrow = timezone.now() + datetime.timedelta(days=1)
        tweet = EventTweet.objects.create(
            event=event,
            text='Something something',
            creator=self.user,
            include_placeholder=True,
            send_date=tomorrow,
        )
        url = reverse('manage:edit_event_tweet', args=(event.id, tweet.id))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Something something' in response.content)
        # tz = pytz.timezone(event.location.timezone)
        data = {
            'text': 'Different Bla ',
            'include_placeholder': True,
            'send_date': tweet.send_date.strftime('%Y-%m-%d %H:%M'),
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        tweet = EventTweet.objects.get(id=tweet.id)
        eq_(tweet.text, 'Different Bla')
        # because we round but they won't be equal, but close
        ok_(abs(tomorrow - tweet.send_date) <= datetime.timedelta(hours=1))

    def test_event_tweets_empty(self):
        event = Event.objects.get(title='Test event')
        url = reverse('manage:event_tweets', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

    def test_event_tweets_states(self):
        event = Event.objects.get(title='Test event')
        assert event in Event.objects.approved()
        group = Group.objects.create(name='testapprover')
        Approval.objects.create(
            event=event,
            group=group,
        )
        assert event not in Event.objects.approved()
        url = reverse('manage:event_tweets', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        tweet = EventTweet.objects.create(
            event=event,
            text='Bla bla',
            send_date=timezone.now(),
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Bla bla' in response.content)
        ok_('Needs to be approved first' in response.content)
        from airmozilla.main.templatetags.jinja_helpers import js_date
        ok_(
            js_date(tweet.send_date.replace(microsecond=0))
            not in response.content
        )

        # also check that 'Bla bla' is shown on the Edit Event page
        edit_url = reverse('manage:event_edit', args=(event.pk,))
        response = self.client.get(edit_url)
        eq_(response.status_code, 200)
        ok_('Bla bla' in response.content)

        tweet.tweet_id = '1234567890'
        tweet.sent_date = (
            timezone.now() -
            datetime.timedelta(days=1)
        )
        tweet.save()

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Bla bla' in response.content)
        ok_(
            'https://twitter.com/%s/status/1234567890'
            % settings.TWITTER_USERNAME
            in response.content
        )
        ok_(
            js_date(tweet.sent_date.replace(microsecond=0))
            in response.content
        )

        tweet.tweet_id = None
        tweet.error = "Some error"
        tweet.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Bla bla' in response.content)
        ok_(
            'https://twitter.com/%s/status/1234567890'
            % settings.TWITTER_USERNAME
            not in response.content
        )
        ok_(
            js_date(tweet.sent_date.replace(microsecond=0))
            in response.content
        )
        ok_('Failed to send' in response.content)

    def test_all_event_tweets_states(self):
        event = Event.objects.get(title='Test event')
        assert event in Event.objects.approved()
        group = Group.objects.create(name='testapprover')
        Approval.objects.create(
            event=event,
            group=group,
        )
        assert event not in Event.objects.approved()
        url = reverse('manage:all_event_tweets_data')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        tweet = EventTweet.objects.create(
            event=event,
            text='Bla bla',
            send_date=timezone.now(),
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        first_tweet, = data['tweets']
        eq_(first_tweet['text'], 'Bla bla')
        ok_(first_tweet['event']['_needs_approval'])

        # also check that 'Bla bla' is shown on the Edit Event page
        edit_url = reverse('manage:event_edit', args=(event.pk,))
        response = self.client.get(edit_url)
        eq_(response.status_code, 200)
        ok_('Bla bla' in response.content)

        tweet.tweet_id = '1234567890'
        tweet.sent_date = timezone.now() - datetime.timedelta(days=1)
        tweet.save()

        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        first_tweet, = data['tweets']

        tweet_url = (
            'https://twitter.com/%s/status/1234567890'
            % settings.TWITTER_USERNAME
        )
        eq_(first_tweet['full_tweet_url'], tweet_url)

        tweet.tweet_id = None
        tweet.error = "Some error"
        tweet.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        first_tweet, = data['tweets']
        ok_('full_tweet_url' not in first_tweet)

        ok_('creator' not in first_tweet)
        assert self.user.email
        tweet.creator = self.user
        tweet.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        first_tweet, = data['tweets']
        eq_(first_tweet['creator'], {'email': self.user.email})

    @mock.patch('airmozilla.manage.views.events.send_tweet')
    def test_force_send_now(self, mocked_send_tweet):
        event = Event.objects.get(title='Test event')

        tweet = EventTweet.objects.create(
            event=event,
            text='Bla bla',
            send_date=timezone.now(),
        )

        def mock_send_tweet(event_tweet):
            event_tweet.tweet_id = '1234567890'
            event_tweet.save()
        mocked_send_tweet.side_effect = mock_send_tweet

        url = reverse('manage:event_tweets', args=(event.pk,))
        response = self.client.post(url, {
            'send': tweet.pk,
        })
        eq_(response.status_code, 302)
        tweet = EventTweet.objects.get(pk=tweet.pk)
        eq_(tweet.tweet_id, '1234567890')

    def test_view_tweet_error(self):
        event = Event.objects.get(title='Test event')

        tweet = EventTweet.objects.create(
            event=event,
            text='Bla bla',
            send_date=timezone.now(),
            error='Crap!'
        )
        url = reverse('manage:event_tweets', args=(event.pk,))
        response = self.client.post(url, {
            'error': tweet.pk,
        })
        eq_(response.status_code, 200)
        eq_(response['content-type'], 'text/plain')
        ok_('Crap!' in response.content)

    def test_cancel_event_tweet(self):
        event = Event.objects.get(title='Test event')

        tweet = EventTweet.objects.create(
            event=event,
            text='Bla bla',
            send_date=timezone.now(),
        )

        url = reverse('manage:event_tweets', args=(event.pk,))
        response = self.client.post(url, {
            'cancel': tweet.pk,
        })
        eq_(response.status_code, 302)
        ok_(not EventTweet.objects.all().count())

    def test_create_event_tweet_with_location_timezone(self):
        event = Event.objects.get(title='Test event')
        event.location = Location.objects.create(
            name='Paris',
            timezone='Europe/Paris'
        )
        event.save()

        # the event must have a real placeholder image
        with open(self.placeholder) as fp:
            response = self.client.post(
                reverse('manage:event_edit', args=(event.pk,)),
                dict(self.event_base_data,
                     title=event.title,
                     short_description="Check out <b>This!</b>",
                     description="Something longer",
                     placeholder_img=fp)
            )
            assert response.status_code == 302, response.status_code

        url = reverse('manage:new_event_tweet', args=(event.pk,))
        now = datetime.datetime.utcnow()
        response = self.client.post(url, {
            'text': 'Bla bla #tag',
            'include_placeholder': True,
            'send_date': now.strftime('%Y-%m-%d 12:00'),
        })
        eq_(response.status_code, 302)
        event_tweet, = EventTweet.objects.all()
        # we specified it as noon in Paris, but the save time
        # will be UTC
        ok_(event_tweet.send_date.hour != 12)
        assert event_tweet.send_date.strftime('%Z') == 'UTC'
