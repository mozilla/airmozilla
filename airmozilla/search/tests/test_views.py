import datetime

from django.test import TestCase
from django.utils.timezone import utc
from django.contrib.auth.models import User

from funfactory.urlresolvers import reverse
from nose.tools import eq_, ok_

from airmozilla.main.models import Event, UserProfile


class TestSearch(TestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']
    placeholder = 'airmozilla/manage/tests/firefox.png'

    def test_basic_search(self):
        Event.objects.all().delete()

        today = datetime.datetime.utcnow()
        event = Event.objects.create(
            title='Entirely Different',
            slug=today.strftime('test-event-%Y%m%d'),
            start_time=today.replace(tzinfo=utc),
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

    def test_basic_search_with_privacy_filter(self):
        Event.objects.all().delete()

        today = datetime.datetime.utcnow()
        event = Event.objects.create(
            title='Entirely Different',
            slug=today.strftime('test-event-%Y%m%d'),
            start_time=today.replace(tzinfo=utc),
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

        today = datetime.datetime.utcnow()
        event1 = Event.objects.create(
            title='Entirely Different',
            slug=today.strftime('test-event-%Y%m%d'),
            start_time=today.replace(tzinfo=utc),
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

        today = datetime.datetime.utcnow()
        event = Event.objects.create(
            title='THis is Different',
            slug=today.strftime('test-event-%Y%m%d'),
            start_time=today.replace(tzinfo=utc),
            placeholder_img=self.placeholder,
            status=Event.STATUS_INITIATED,
            description="These are my words."
        )
        assert event not in Event.objects.approved()

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

    def test_search_by_stemming(self):
        Event.objects.all().delete()

        today = datetime.datetime.utcnow()
        event = Event.objects.create(
            title='Engagement Discussion',
            slug=today.strftime('test-event-%Y%m%d'),
            start_time=today.replace(tzinfo=utc),
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

        today = datetime.datetime.utcnow()
        event = Event.objects.create(
            title='Engagement Discussion',
            slug=today.strftime('test-event-%Y%m%d'),
            start_time=today.replace(tzinfo=utc),
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

        today = datetime.datetime.utcnow()
        event1 = Event.objects.create(
            title='Blobber Fest',
            slug='blobbering',
            start_time=today.replace(tzinfo=utc),
            placeholder_img=self.placeholder,
            status=Event.STATUS_SCHEDULED,
            description="These are my words."
        )
        assert event1 in Event.objects.approved()

        event2 = Event.objects.create(
            title='Beauty and the Beast',
            slug='beauty-and-beast',
            start_time=today.replace(tzinfo=utc),
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
