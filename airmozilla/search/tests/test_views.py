import datetime
import urllib
import os
import json

from django.utils import timezone
from django.utils.timezone import utc
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.utils.encoding import smart_text

from nose.tools import eq_, ok_

from airmozilla.search.models import LoggedSearch, SavedSearch
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
        ok_(event.title in smart_text(response.content))

        app = Approval.objects.create(event=event)
        response = self.client.get(url, {'q': 'test'})
        eq_(response.status_code, 200)
        ok_(event.title in smart_text(response.content))

        app.processed = True
        app.save()
        response = self.client.get(url, {'q': 'test'})
        eq_(response.status_code, 200)
        ok_(event.title in smart_text(response.content))

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

        # Do the same but using a saved search
        savedsearch = SavedSearch.objects.create(
            user=User.objects.create(username='anybody'),
            filters={
                'title': {'include': 'TesT EveNt'},
            }
        )
        response = self.client.get(url, {'ss': savedsearch.id})
        eq_(response.status_code, 200)
        # When no search highlighting, the title appears in the thumbnail's
        # title attribute and in the title link itself.
        eq_(response.content.count('Test event'), 10 * 2)

        response = self.client.get(url, {'ss': savedsearch.id, 'page': 2})
        eq_(response.status_code, 200)
        eq_(response.content.count('Test event'), 5 * 2)

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

    def test_savesearch_link(self):
        # make a search
        url = reverse('search:home')
        response = self.client.get(url, {'q': 'firefox'})
        eq_(response.status_code, 200)

        savesearch_url = reverse('search:savesearch')
        ok_(savesearch_url not in response.content)

        user = self._login()
        response = self.client.get(url, {'q': 'firefox'})
        eq_(response.status_code, 200)
        response_content = response.content.decode('utf-8')
        ok_(savesearch_url in response_content)

        response = self.client.post(savesearch_url, {'q': ''})
        eq_(response.status_code, 400)

        response = self.client.post(savesearch_url, {'q': 'xx'})
        eq_(response.status_code, 400)

        response = self.client.post(savesearch_url, {'q': 'firefox'})
        eq_(response.status_code, 302)
        savedsearch = SavedSearch.objects.get(user=user)
        eq_(savedsearch.filters['title']['include'], 'firefox')

    def test_savesearch_link_advanced(self):
        tag = Tag.objects.create(name='Tag1')
        channel = Channel.objects.create(name='Channel1', slug='channel')
        user = self._login()
        url = reverse('search:savesearch')
        response = self.client.post(url, {
            'q': 'firefox tag:tag1 channel:channel1'
        })
        eq_(response.status_code, 302)
        savedsearch = SavedSearch.objects.get(user=user)
        eq_(savedsearch.filters['title']['include'], 'firefox')
        eq_(savedsearch.filters['tags']['include'], [tag.id])
        eq_(savedsearch.filters['channels']['include'], [channel.id])

    def test_savesearch_avoid_duplicates(self):
        tag = Tag.objects.create(name='Tag1')
        channel = Channel.objects.create(name='Channel1', slug='channel')
        user = self._login()
        SavedSearch.objects.create(
            user=user,
            filters={
                'title': {'include': 'firefox'},
                'tags': {'include': [tag.id]},
                'channels': {'include': [channel.id]},
            }
        )
        url = reverse('search:savesearch')
        response = self.client.post(url, {
            'q': 'firefox tag:tag1 channel:channel1'
        })
        eq_(response.status_code, 302)
        eq_(SavedSearch.objects.all().count(), 1)

    def test_savedsearch(self):
        user = User.objects.create_user(
            'bob', 'bob@example.com', 'secret'
        )
        savedsearch = SavedSearch.objects.create(
            user=user,
            filters={
                'title': {
                    'include': 'firefox'
                }
            },
        )
        url = reverse('search:savedsearch', args=(savedsearch.id,))
        response = self.client.get(url)
        eq_(response.status_code, 302)

        assert self.client.login(username='bob', password='secret')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        tag1 = Tag.objects.create(name='tag1')
        tag2 = Tag.objects.create(name='tag2')
        tag3 = Tag.objects.create(name='tag3')

        channel1 = Channel.objects.create(name='Channel1', slug='c1')
        channel2 = Channel.objects.create(name='Channel2', slug='c2')

        data = {
            'name': 'My name',
            'title_include': 'word',
            'title_exclude': 'notword',
            'tags_include': [tag1.id, tag2.id],
            'tags_exclude': [tag3.id],
            'channels_include': [channel1.id],
            'channels_exclude': [channel2.id],
            'privacy': [
                Event.PRIVACY_CONTRIBUTORS,
                Event.PRIVACY_COMPANY,
            ],
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)

        savedsearch = SavedSearch.objects.get(id=savedsearch.id)
        eq_(savedsearch.name, data['name'])
        eq_(savedsearch.filters['privacy'], data['privacy'])
        eq_(savedsearch.filters['title']['include'], 'word')
        eq_(savedsearch.filters['title']['exclude'], 'notword')
        eq_(savedsearch.filters['tags']['include'], [tag1.id, tag2.id])
        eq_(savedsearch.filters['tags']['exclude'], [tag3.id])
        eq_(savedsearch.filters['channels']['include'], [channel1.id])
        eq_(savedsearch.filters['channels']['exclude'], [channel2.id])

        # also, check how many events can be found with this search
        response = self.client.get(url, {'sample': True})
        eq_(response.status_code, 200)
        events = json.loads(response.content)['events']
        eq_(events, 0)

    def test_save_someone_elses_saved_search(self):
        original_user = User.objects.create_user(
            'some', 'one@example.com', 'secret'
        )
        savedsearch = SavedSearch.objects.create(
            user=original_user,
            filters={
                'title': {
                    'include': 'firefox'
                }
            },
        )
        user = self._login()
        url = reverse('search:savedsearch', args=(savedsearch.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        data = {
            'name': 'Other name',
            'title_include': 'Other',
        }

        response = self.client.post(url, data)
        eq_(response.status_code, 302)

        ok_(not response['location'].endswith(url))

        assert SavedSearch.objects.all().count() == 2
        savedsearch = SavedSearch.objects.get(user=user)
        new_url = reverse('search:savedsearch', args=(savedsearch.id,))
        assert url != new_url
        ok_(response['location'].endswith(new_url))

        eq_(savedsearch.name, data['name'])
        eq_(savedsearch.filters['title']['include'], 'Other')

    def test_savedsearches(self):
        # first render the basic savedsearches page
        url = reverse('search:savedsearches')
        response = self.client.get(url)
        eq_(response.status_code, 302)

        user = self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # now for the data
        url = reverse('search:savedsearches_data')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content)['savedsearches'], [])

        # create a sample saved search
        tag1 = Tag.objects.create(name='tag1')
        tag2 = Tag.objects.create(name='tag2')

        channel1 = Channel.objects.create(name='Channel1', slug='c1')
        channel2 = Channel.objects.create(name='Channel2', slug='c2')

        savedsearch = SavedSearch.objects.create(
            user=user,
            name='Some Name',
            filters={
                'title': {
                    'include': 'INCLUDE',
                    'exclude': 'EXCLUDE',
                },
                'tags': {
                    'include': [tag1.id],
                    'exclude': [tag2.id],
                },
                'channels': {
                    'include': [channel1.id],
                    'exclude': [channel2.id],
                },
                'privacy': [
                    Event.PRIVACY_CONTRIBUTORS,
                    Event.PRIVACY_COMPANY,
                ]
            }
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        savedsearches = json.loads(response.content)['savedsearches']
        eq_(len(savedsearches), 1)
        first, = savedsearches
        eq_(first['modified'], savedsearch.modified.isoformat())
        eq_(first['name'], savedsearch.name)
        eq_(first['id'], savedsearch.id)
        eq_(first['summary'], savedsearch.summary)

        # We should also have a list of URLs.
        urls = json.loads(response.content)['urls']
        # One of which is the right feed URL base
        eq_(urls['feed'], reverse('main:feed', args=('company',)))

        # but if we're just a contributor the link should be different
        UserProfile.objects.create(
            user=user,
            contributor=True
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        urls = json.loads(response.content)['urls']
        eq_(urls['feed'], reverse('main:feed', args=('contributors',)))

        # Now delete it.
        delete_url = reverse(
            'search:delete_savedsearch',
            args=(savedsearch.id,)
        )
        # But before we try to do that, let's make sure it's not possible
        # if it belongs to someone else.
        other_user = User.objects.create(username='other')
        savedsearch.user = other_user
        savedsearch.save()
        response = self.client.post(delete_url)
        eq_(response.status_code, 403)

        savedsearch.user = user
        savedsearch.save()
        response = self.client.post(delete_url)
        eq_(response.status_code, 200)
        ok_(not SavedSearch.objects.all())

    def test_new_savedsearch(self):
        url = reverse('search:new_savedsearch')
        response = self.client.get(url)
        eq_(response.status_code, 302)

        user = self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # try to submit the form with NOTHING in it
        response = self.client.post(url, {})
        eq_(response.status_code, 200)
        ok_('Nothing entered' in response.content)

        # just name is not good enough
        response = self.client.post(url, {'name': 'Something'})
        eq_(response.status_code, 200)
        ok_('Nothing entered' in response.content)

        # now actually save something
        response = self.client.post(url, {
            'name': 'Something',
            'title_exclude': 'Curse word',
        })
        eq_(response.status_code, 302)

        savedsearch, = SavedSearch.objects.filter(user=user)
        eq_(savedsearch.name, 'Something')
        eq_(savedsearch.filters['title']['exclude'], 'Curse word')
