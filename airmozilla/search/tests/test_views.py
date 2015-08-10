import datetime
import urllib
import os

from django.utils import timezone
from django.utils.timezone import utc
from django.contrib.auth.models import User

from funfactory.urlresolvers import reverse
from nose.tools import eq_, ok_

from airmozilla.search.models import LoggedSearch
from airmozilla.main.models import Event, UserProfile, Tag, Channel, Approval
from airmozilla.base.tests.testbase import DjangoTestCase


class TestSearch(DjangoTestCase):
    placeholder_path = 'airmozilla/manage/tests/firefox.png'
    placeholder = os.path.basename(placeholder_path)

    def test_basic_search(self):
        Event.objects.all().delete()

        today = timezone.now()
        event = Event.objects.create(
            title='Entirely Different',
            slug=today.strftime('test-event-%Y%m%d'),
            start_time=today,
            placeholder_img=self.placeholder,
            status=Event.STATUS_INITIATED,
            description="These are my words."
        )
        assert event not in Event.objects.approved()

        url = reverse('search:home')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        response = self.client.get(url, {'q': 'entirely'})
        eq_(response.status_code, 200)
        ok_('Nothing found' in response.content)

        event.status = Event.STATUS_SCHEDULED
        event.save()
        assert event in Event.objects.approved()
        assert event.privacy == Event.PRIVACY_PUBLIC

        response = self.client.get(url, {'q': 'entirely'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(event.title in response.content)
        ok_('value="entirely"' in response.content)

    def test_search_unapproved_events_anonymous(self):
        event = Event.objects.get(title='Test event')
        url = reverse('search:home')
        response = self.client.get(url, {'q': 'junk'})
        eq_(response.status_code, 200)
        ok_(event.title not in response.content)

        response = self.client.get(url, {'q': 'test'})
        eq_(response.status_code, 200)
        ok_(event.title in response.content)

        app = Approval.objects.create(event=event)
        response = self.client.get(url, {'q': 'test'})
        eq_(response.status_code, 200)
        ok_(event.title not in response.content)

        app.processed = True
        app.save()
        response = self.client.get(url, {'q': 'test'})
        eq_(response.status_code, 200)
        ok_(event.title not in response.content)

        app.approved = True
        app.save()
        response = self.client.get(url, {'q': 'test'})
        eq_(response.status_code, 200)
        ok_(event.title in response.content)

    def test_search_unapproved_events_signed_in(self):
        event = Event.objects.get(title='Test event')
        url = reverse('search:home')
        self._login()
        response = self.client.get(url, {'q': 'test'})
        eq_(response.status_code, 200)
        ok_(event.title in response.content)

        app = Approval.objects.create(event=event)
        response = self.client.get(url, {'q': 'test'})
        eq_(response.status_code, 200)
        ok_(event.title in response.content)

        app.processed = True
        app.save()
        response = self.client.get(url, {'q': 'test'})
        eq_(response.status_code, 200)
        ok_(event.title in response.content)

    def test_basic_search_with_privacy_filter(self):
        Event.objects.all().delete()

        today = timezone.now()
        event = Event.objects.create(
            title='Entirely Different',
            slug=today.strftime('test-event-%Y%m%d'),
            start_time=today,
            placeholder_img=self.placeholder,
            status=Event.STATUS_SCHEDULED,
            description="These are my words."
        )
        assert event in Event.objects.approved()

        url = reverse('search:home')
        response = self.client.get(url, {'q': 'entirely'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(event.title in response.content)

        event.privacy = Event.PRIVACY_CONTRIBUTORS
        event.save()

        response = self.client.get(url, {'q': 'entirely'})
        eq_(response.status_code, 200)
        ok_('Nothing found' in response.content)

        contributor = User.objects.create_user(
            'nigel', 'nigel@live.com', 'secret'
        )
        user_profile = UserProfile.objects.create(
            user=contributor,
            contributor=True
        )
        assert self.client.login(username='nigel', password='secret')
        response = self.client.get(url, {'q': 'entirely'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(event.title in response.content)

        event.privacy = Event.PRIVACY_COMPANY
        event.save()
        response = self.client.get(url, {'q': 'entirely'})
        eq_(response.status_code, 200)
        ok_('Nothing found' in response.content)

        user_profile.contributor = False
        user_profile.save()
        response = self.client.get(url, {'q': 'entirely'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(event.title in response.content)

    def test_search_ordering(self):
        Event.objects.all().delete()

        today = timezone.now()
        event1 = Event.objects.create(
            title='Entirely Different',
            slug=today.strftime('test-event-%Y%m%d'),
            start_time=today,
            placeholder_img=self.placeholder,
            status=Event.STATUS_SCHEDULED,
            description="A different word is not mentioned here."
        )
        assert event1 in Event.objects.approved()

        yesterday = today - datetime.timedelta(days=1)
        event2 = Event.objects.create(
            title='Muscle Belts',
            slug=yesterday.strftime('test-event-%Y%m%d'),
            start_time=yesterday.replace(tzinfo=utc),
            placeholder_img=self.placeholder,
            status=Event.STATUS_SCHEDULED,
            description="The word entirely appears here"
        )
        assert event2 in Event.objects.approved()

        url = reverse('search:home')
        response = self.client.get(url, {'q': 'entirely'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(event1.title in response.content)
        ok_(event2.title in response.content)
        # event1 should appear ahead of event2
        # because event1 has the word "entirely" in the title
        ok_(response.content.find(event1.title) <
            response.content.find(event2.title))

        response = self.client.get(url, {'q': 'words'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(event1.title in response.content)
        ok_(event2.title in response.content)
        # "word" appears in both but event1 is newer
        ok_(response.content.find(event1.title) <
            response.content.find(event2.title))

    def test_search_by_stopwords(self):
        Event.objects.all().delete()

        today = timezone.now()
        event = Event.objects.create(
            title='THis is Different',
            slug=today.strftime('test-event-%Y%m%d'),
            start_time=today,
            placeholder_img=self.placeholder,
            status=Event.STATUS_SCHEDULED,
            description="These are my words."
        )
        assert event in Event.objects.approved()

        url = reverse('search:home')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        response = self.client.get(url, {'q': 'this'})
        eq_(response.status_code, 200)
        ok_('Nothing found' in response.content)
        response = self.client.get(url, {'q': 'this is are these'})
        eq_(response.status_code, 200)
        ok_('Nothing found' in response.content)
        response = self.client.get(url, {'q': 'are'})
        eq_(response.status_code, 200)
        ok_('Nothing found' in response.content)

    def test_search_with_strange_characters(self):
        Event.objects.all().delete()

        today = timezone.now()
        event = Event.objects.create(
            title='THis is Different',
            slug=today.strftime('test-event-%Y%m%d'),
            start_time=today,
            placeholder_img=self.placeholder,
            status=Event.STATUS_SCHEDULED,
            description="These are my words."
        )
        assert event in Event.objects.approved()

        url = reverse('search:home')

        # first check that specific words work
        response = self.client.get(url, {'q': 'WORD'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(event.title in response.content)

        response = self.client.get(url, {'q': "O'Brian Should Work"})
        eq_(response.status_code, 200)
        ok_('Nothing found' in response.content)

        response = self.client.get(url, {'q': 'are my'})
        eq_(response.status_code, 200)
        ok_('Nothing found' in response.content)

        # this won't allow the automatic OR
        response = self.client.get(url, {'q': 'WORDS | LETTERS'})
        eq_(response.status_code, 200)
        ok_('Nothing found' in response.content)

        response = self.client.get(url, {'q': 'WORDS & LETTERS'})
        eq_(response.status_code, 200)
        ok_('Nothing found' in response.content)

        response = self.client.get(url, {'q': 'WORDS LETTERS'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(event.title in response.content)

    def test_search_with_nothing(self):
        Event.objects.all().delete()

        today = timezone.now()
        event = Event.objects.create(
            title='THis is Different',
            slug=today.strftime('test-event-%Y%m%d'),
            start_time=today,
            placeholder_img=self.placeholder,
            status=Event.STATUS_SCHEDULED,
            description="These are my words."
        )
        assert event in Event.objects.approved()

        url = reverse('search:home')
        response = self.client.get(url, {'q': ''})
        eq_(response.status_code, 200)
        ok_(event.title not in response.content)

    def test_search_by_stemming(self):
        Event.objects.all().delete()

        today = timezone.now()
        event = Event.objects.create(
            title='Engagement Discussion',
            slug=today.strftime('test-event-%Y%m%d'),
            start_time=today,
            placeholder_img=self.placeholder,
            status=Event.STATUS_SCHEDULED,
            description="These are my words."
        )
        assert event in Event.objects.approved()

        url = reverse('search:home')
        response = self.client.get(url, {'q': 'discuss'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(event.title in response.content)

        response = self.client.get(url, {'q': 'discussions'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(event.title in response.content)

        response = self.client.get(url, {'q': 'engage'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(event.title in response.content)

    def test_search_with_highlight(self):
        Event.objects.all().delete()

        today = timezone.now()
        event = Event.objects.create(
            title='Engagement Discussion',
            slug=today.strftime('test-event-%Y%m%d'),
            start_time=today,
            placeholder_img=self.placeholder,
            status=Event.STATUS_SCHEDULED,
            description="These are my words."
        )
        assert event in Event.objects.approved()

        url = reverse('search:home')
        response = self.client.get(url, {'q': 'discuss'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_('<b>Discussion</b>' in response.content)

        event.title += ' <input name="foo">'
        event.save()
        response = self.client.get(url, {'q': 'discuss'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_('<b>Discussion</b>' in response.content)
        ok_('<input name="foo">' not in response.content)

        response = self.client.get(url, {'q': 'WORD'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        # because it's not the short description
        ok_('<b>words</b>' not in response.content)

        event.short_description = "These are your words."
        event.save()
        response = self.client.get(url, {'q': 'WORD'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_('<b>words</b>' in response.content)

        event.short_description += ' <script>alert("xxx")</script>'
        event.save()
        response = self.client.get(url, {'q': 'WORD'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_('<script>alert' not in response.content)

    def test_searching_multi_words_finding_with_or(self):

        Event.objects.all().delete()

        today = timezone.now()
        event1 = Event.objects.create(
            title='Blobber Fest',
            slug='blobbering',
            start_time=today,
            placeholder_img=self.placeholder,
            status=Event.STATUS_SCHEDULED,
            description="These are my words."
        )
        assert event1 in Event.objects.approved()

        event2 = Event.objects.create(
            title='Beauty and the Beast',
            slug='beauty-and-beast',
            start_time=today,
            placeholder_img=self.placeholder,
            status=Event.STATUS_SCHEDULED,
            description="These are other words."
        )
        assert event2 in Event.objects.approved()

        url = reverse('search:home')

        response = self.client.get(url, {'q': 'BLOBBER'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(event1.title in response.content)
        ok_(event2.title not in response.content)

        response = self.client.get(url, {'q': 'BEAST'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(event1.title not in response.content)
        ok_(event2.title in response.content)

        response = self.client.get(url, {'q': 'BLOBBER BEAST'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(event1.title in response.content)
        ok_(event2.title in response.content)

    def test_search_with_sql_injection(self):
        assert Event.objects.approved()
        url = reverse('search:home')
        q = '1" onmouseover=prompt(931357) bad="'
        response = self.client.get(url, {'q': q})
        eq_(response.status_code, 200)
        ok_('Nothing found' in response.content)

    def test_search_by_transcript(self):
        assert Event.objects.approved()
        url = reverse('search:home')
        q = 'fingerfood'
        response = self.client.get(url, {'q': q})
        eq_(response.status_code, 200)
        ok_('Nothing found' in response.content)

        event, = Event.objects.approved()
        event.transcript = 'I love fingerfoods'
        event.save()
        response = self.client.get(url, {'q': q})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(event.title in response.content)
        ok_('found by transcript' in response.content)

        # but if the event is found because of the description...
        event.short_description = "Peter talks about his love for fingerfood"
        event.save()
        response = self.client.get(url, {'q': q})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(event.title in response.content)
        ok_('found by transcript' not in response.content)

    def test_paginated_search(self):
        event = Event.objects.get(title='Test event')
        for i in range(14):
            Event.objects.create(
                title='Test event %d' % (i + 1),
                short_description=event.short_description,
                description=event.description,
                start_time=event.start_time,
                archive_time=event.archive_time,
                location=event.location,
                privacy=event.privacy,
                status=event.status,
                placeholder_img=event.placeholder_img,
            )

        url = reverse('search:home')
        response = self.client.get(url, {'q': 'TEST EVENT'})
        eq_(response.status_code, 200)
        eq_(response.content.count('Test event'), 10)

        response = self.client.get(url, {'q': 'TEST EVENT', 'page': 2})
        eq_(response.status_code, 200)
        eq_(response.content.count('Test event'), 5)

        # but don't try to mess with it
        response = self.client.get(url, {'q': 'TEST EVENT', 'page': 0})
        eq_(response.status_code, 400)

    def test_search_by_tag(self):
        assert Event.objects.approved()
        url = reverse('search:home')
        response = self.client.get(url, {'q': 'tag: mytag'})
        eq_(response.status_code, 200)
        ok_('Nothing found' in response.content)
        tag = Tag.objects.create(name='mytag')
        event = Event.objects.get(title='Test event')
        event.tags.add(tag)

        response = self.client.get(url, {'q': 'tag: mytag'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(event.title in response.content)

        # should work case insensitively
        response = self.client.get(url, {'q': 'TAG: MYTAG'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(event.title in response.content)

        # combine with something else to be found
        response = self.client.get(url, {'q': 'Test tag:mytag'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(event.title in response.content)

        # combine with something else to be NOT found
        response = self.client.get(url, {'q': 'Somethingelse tag:mytag'})
        eq_(response.status_code, 200)
        ok_('Nothing found' in response.content)

    def test_search_and_suggest_tags(self):
        url = reverse('search:home')
        event = Event.objects.get(title='Test event')
        tag = Tag.objects.create(name='rust')
        event.tags.add(tag)

        response = self.client.get(url, {'q': 'RUst'})
        eq_(response.status_code, 200)
        # because neither title or description contains this
        ok_('Nothing found' in response.content)
        tag_search_url = url + '?q=%s' % urllib.quote_plus('tag: rust')
        ok_(tag_search_url in response.content)

        # But searching for parts of the tag word should not suggest the
        # tag.
        # See https://bugzilla.mozilla.org/show_bug.cgi?id=1072985
        response = self.client.get(url, {'q': 'rusty'})
        eq_(response.status_code, 200)
        ok_(tag_search_url not in response.content)

    def test_search_and_suggest_multiple_tags(self):
        url = reverse('search:home')
        event = Event.objects.get(title='Test event')

        tag = Tag.objects.create(name='mytag')
        event.tags.add(tag)
        othertag = Tag.objects.create(name='other tag')
        event.tags.add(othertag)

        response = self.client.get(url, {'q': 'mytag other tag'})
        eq_(response.status_code, 200)
        # because neither title or description contains this
        ok_('Nothing found' in response.content)
        tag_search_url = (
            url + '?q=%s' % urllib.quote_plus('other tag tag: mytag')
        )
        ok_(tag_search_url in response.content)
        othertag_search_url = (
            url + '?q=%s' % urllib.quote_plus('mytag tag: other tag')
        )
        ok_(othertag_search_url in response.content)

    def test_search_by_channel(self):
        assert Event.objects.approved()
        url = reverse('search:home')
        event = Event.objects.get(title='Test event')
        response = self.client.get(url, {'q': 'channel: Grow Mozilla'})
        eq_(response.status_code, 200)
        ok_('Nothing found' in response.content)
        channel = Channel.objects.create(
            name='Grow Mozilla', slug='gr-mozilla')
        event.channels.add(channel)

        response = self.client.get(url, {'q': 'channel: Grow Mozilla'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(event.title in response.content)

        # should work case insensitively
        response = self.client.get(url, {'q': 'CHANNEL: GROW mozilla'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(event.title in response.content)

        # combine with something else to be found
        response = self.client.get(url, {'q': 'Test channel:grow mozilla'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(event.title in response.content)

        # combine with something else to be NOT found
        response = self.client.get(
            url, {'q': 'Somethingelse channel:grow mozilla'}
        )
        eq_(response.status_code, 200)
        ok_('Nothing found' in response.content)

    def test_search_and_suggest_channels(self):
        url = reverse('search:home')
        event = Event.objects.get(title='Test event')
        channel = Channel.objects.create(name='Grow Mozilla')
        event.channels.add(channel)

        response = self.client.get(url, {'q': 'grow mozilla'})
        eq_(response.status_code, 200)
        # because neither title or description contains this
        ok_('Nothing found' in response.content)
        channel_search_url = (
            url + '?q=%s' % urllib.quote_plus('channel: Grow Mozilla')
        )
        ok_(channel_search_url in response.content)

        # See https://bugzilla.mozilla.org/show_bug.cgi?id=1072985
        Channel.objects.create(name='Rust', slug='rust')
        channel_search_url = (
            url + '?q=%s' % urllib.quote_plus('y channel: Rust')
        )
        response = self.client.get(url, {'q': 'rusty'})
        eq_(response.status_code, 200)
        ok_(channel_search_url not in response.content)

    def test_logged_search(self):
        url = reverse('search:home')
        response = self.client.get(url, {'q': 'TesT'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)

        logged_search = LoggedSearch.objects.get(
            term='TesT',
            results=1,
            page=1,
        )

        # now after that, click on the found event
        event = Event.objects.get(title='Test event')
        event_url = reverse('main:event', args=(event.slug,))
        ok_(event_url in response.content)
        response = self.client.get(event_url)
        eq_(response.status_code, 200)

        # using a session it should now record that that search
        # lead to clicking this event
        logged_search = LoggedSearch.objects.get(pk=logged_search.pk)
        eq_(logged_search.event_clicked, event)

    def test_logged_search_not_empty_searches(self):
        url = reverse('search:home')
        response = self.client.get(url, {'q': ''})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(not LoggedSearch.objects.all())

        # or something too short
        response = self.client.get(url, {'q': '1'})
        eq_(response.status_code, 200)
        ok_('Too short' in response.content)
        ok_(not LoggedSearch.objects.all())

        response = self.client.get(url, {'q': ' ' * 10})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_(not LoggedSearch.objects.all())

        # but search by channel or tag without a wildcard should log
        response = self.client.get(url, {'q': 'channel: Foo'})
        eq_(response.status_code, 200)
        ok_('Nothing found' in response.content)
        ok_(LoggedSearch.objects.all())

    def test_unicode_next_page_links(self):
        """https://bugzilla.mozilla.org/show_bug.cgi?id=1079370"""
        event = Event.objects.get(title='Test event')
        for i in range(20):
            Event.objects.create(
                title=u'T\xe4st event %d' % (i + 1),
                short_description=event.short_description,
                description=event.description,
                start_time=event.start_time,
                archive_time=event.archive_time,
                location=event.location,
                privacy=event.privacy,
                status=event.status,
                placeholder_img=event.placeholder_img,
            )
        url = reverse('search:home')
        response = self.client.get(url, {'q': u'T\xe4sT'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)

    def test_event_channels(self):
        # tests if channels were in events from search
        event = Event.objects.get(title='Test event')
        channel = Channel.objects.create(
            name='TestChannel', slug='test-channel')
        event.channels.add(channel)

        url = reverse('search:home')
        response = self.client.get(url, {'q': 'Test event'})
        eq_(response.status_code, 200)
        ok_(channel.slug in response.content)
        ok_(channel.name in response.content)

    def test_searched_event_has_star(self):
        Event.objects.all().delete()

        today = timezone.now()
        event = Event.objects.create(
            title='Engagement Discussion',
            slug=today.strftime('test-event-%Y%m%d'),
            start_time=today,
            placeholder_img=self.placeholder,
            status=Event.STATUS_SCHEDULED,
            description="These are my words."
        )
        assert event in Event.objects.approved()

        url = reverse('search:home')
        response = self.client.get(url, {'q': 'discuss'})
        eq_(response.status_code, 200)
        ok_('Nothing found' not in response.content)
        ok_('class="star"' in response.content)
