import json

from nose.tools import eq_, ok_

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.main.models import Event, CuratedGroup
from airmozilla.starred.models import (
    StarredEvent,
)


class TestStarredEvent(DjangoTestCase):
    sync_url = reverse('starred:sync')
    home_url = reverse('starred:home')

    def setUp(self):
        super(TestStarredEvent, self).setUp()

        # The event we're going to clone needs to have a real image
        # associated with it so it can be rendered.
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)

    def create_event(self, title):
        # instantiate test event
        event = Event.objects.get(title='Test event')
        event_count = Event.objects.count()

        # create more events
        return Event.objects.create(
            title=title,
            slug='event' + str(event_count),
            description=event.description,
            start_time=event.start_time,
            archive_time=event.archive_time,
            privacy=Event.PRIVACY_PUBLIC,
            placeholder_img=event.placeholder_img,
            location=event.location,
        )

    def test_sync_starred_events(self):

        url = self.sync_url
        self._login(username='lisa')
        event1 = Event.objects.get(title='Test event')

        response = self.client.get(url)
        eq_(response.status_code, 200)

        # get the empty list of event ids in json format
        structure = json.loads(response.content)
        csrf_token = structure['csrf_token']
        eq_(structure, {'csrf_token': csrf_token, 'ids': []})

        # add an event id to the list
        structure['ids'].append(event1.id)
        # send synced list to browser
        response = self.client.post(url, {'ids': structure['ids']})
        # get the list and verify it was updated
        structure = json.loads(response.content)
        eq_(structure, {'csrf_token': csrf_token, 'ids': [event1.id]})

    def test_removed_starred_event(self):
        url = self.sync_url
        user = self._login(username='lisa')

        event1 = Event.objects.get(title='Test event')
        event2 = self.create_event('Test event 2')

        StarredEvent.objects.create(user=user, event=event1)
        StarredEvent.objects.create(user=user, event=event2)

        response = self.client.post(url, {'ids': [event1.id]})
        eq_(response.status_code, 200)

        ok_(StarredEvent.objects.filter(event=event1.id))
        ok_(not StarredEvent.objects.filter(event=event2.id))

    def test_invalid_starred_event_id(self):

        url = self.sync_url
        self._login(username='lisa')
        event1 = Event.objects.get(title='Test event')

        response = self.client.get(url)
        eq_(response.status_code, 200)

        # get the empty list of event ids in json format
        structure = json.loads(response.content)
        csrf_token = structure['csrf_token']
        eq_(structure, {'csrf_token': csrf_token, 'ids': []})

        # add event id to the list
        structure['ids'].append(event1.id)
        # send list to the browser
        response = self.client.post(url, {'ids': structure['ids']})
        # get the list and verify it was updated
        structure = json.loads(response.content)
        eq_(structure, {'csrf_token': csrf_token, 'ids': [event1.id]})

        # delete event
        event1.delete()
        # send updated list to the browser
        response = self.client.post(url, {'ids': structure['ids']})
        # get the list and verify it was updated
        structure = json.loads(response.content)
        eq_(structure, {'csrf_token': csrf_token, 'ids': []})

    def test_anonymous_user(self):

        url = self.sync_url

        send = {'ids': [23, 24]}

        # send list to the browser
        response = self.client.post(url, send)
        receive = json.loads(response.content)
        csrf_token = receive['csrf_token']
        # verify the list is returned to the user
        eq_(receive, {'csrf_token': csrf_token, 'ids': []})

    def test_display_starred_events(self):

        # create the url
        url = self.home_url

        user1 = self._login(username='lisa')
        # create second user
        user2 = User.objects.create(
            username='andrew'
        )

        # create events
        event1 = self.create_event('Test Event 1')
        event2 = self.create_event('Test Event 2')
        event3 = self.create_event('Test Event 3')

        # star events for logged in user
        StarredEvent.objects.create(user=user1, event=event1)
        StarredEvent.objects.create(user=user1, event=event2)

        # star events for second user
        StarredEvent.objects.create(user=user2, event=event2)
        StarredEvent.objects.create(user=user2, event=event3)

        response = self.client.get(url)
        eq_(response.status_code, 200)

        # verify only logged in user's starred events are displayed
        ok_(event1.title in response.content)
        ok_(event2.title in response.content)
        ok_(event3.title not in response.content)

        # load page with an AJAX GET
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        eq_(response.status_code, 200)

        # verify entire page is not returned
        ok_('</head>' not in response.content)
        ok_('</body>' not in response.content)

        # verify correct events are displayed
        ok_(event1.title in response.content)
        ok_(event2.title in response.content)
        ok_(event3.title not in response.content)

    def test_display_starred_events_belonging_to_curated_groups(self):
        url = self.home_url

        user = self._login(username='lisa')
        event = self.create_event('Test Event 1')
        event.privacy = Event.PRIVACY_CONTRIBUTORS
        event.save()
        CuratedGroup.objects.create(
            event=event,
            name='Some Curated Group'
        )
        StarredEvent.objects.create(user=user, event=event)

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(event.title in response.content)
        ok_('Some Curated Group' in response.content)

        # load page with an AJAX GET
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        eq_(response.status_code, 200)

        # verify correct events are displayed
        ok_(event.title in response.content)
        ok_('Some Curated Group' in response.content)

    def test_anonymous_starred_events(self):

        # create url
        url = self.home_url

        response = self.client.get(url)
        eq_(response.status_code, 200)

        # verify correct page loads
        ok_("Please wait. Loading your starred events..." in response.content)

        # create events
        event1 = self.create_event('Test Event 1')
        event2 = self.create_event('Test Event 2')
        event3 = self.create_event('Test Event 3')

        # load page with an AJAX GET. `+ 1` tests that an invalid
        # event id does not error when passed in the URL
        response = self.client.get(
            url,
            {'ids': '%d,%d,%d' % (event1.id, event2.id, event3.id + 1)},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        eq_(response.status_code, 200)

        # verify entire page is not returned
        ok_('</head>' not in response.content)
        ok_('</body>' not in response.content)

        # verify correct events load
        ok_(event1.title in response.content)
        ok_(event2.title in response.content)
        ok_(event3.title not in response.content)

    def test_anonymous_starred_events_by_privacy(self):
        # create events
        event1 = self.create_event('Test Event 1')
        event2 = self.create_event('Test Event 2')
        event2.privacy = Event.PRIVACY_CONTRIBUTORS
        event2.save()
        event3 = self.create_event('Test Event 3')
        event3.privacy = Event.PRIVACY_COMPANY
        event3.save()

        # load page with an AJAX GET. `+ 1` tests that an invalid
        # event id does not error when passed in the URL
        response = self.client.get(
            self.home_url,
            {'ids': '%d,%d,%d' % (event1.id, event2.id, event3.id)},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        eq_(response.status_code, 200)

        # verify correct events load
        ok_(event1.title in response.content)
        ok_(event2.title not in response.content)
        ok_(event3.title not in response.content)

    def test_anonymous_starred_events_bad_ids(self):
        # create events
        event1 = self.create_event('Test Event 1')

        # load page with an AJAX GET. `+ 1` tests that an invalid
        # event id does not error when passed in the URL
        response = self.client.get(
            self.home_url,
            {'ids': '%d,9999,x' % (event1.id,)},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        eq_(response.status_code, 400)

    def test_event_pagination(self):
        url = self.home_url
        user = self._login(username='lisa')

        events = []

        for i in range(25):
            event = self.create_event("Event Title %d" % (i + 1))
            StarredEvent.objects.create(user=user, event=event)
            events.append(event)

        response = self.client.get(url)
        eq_(response.status_code, 200)

        for i, event in enumerate(events):
            match = 'data-id="%d"' % event.id
            if i < 10:
                ok_(match in response.content, i)
            else:
                ok_(match not in response.content, i)

        output = response.content.decode('utf-8')
        ok_('href="%s"' % reverse('starred:home', args=(2,)) in output)
        ok_('href="%s"' % reverse('starred:home', args=(0,)) not in output)

        response = self.client.get(url + 'page/2/')
        eq_(response.status_code, 200)

        for i, event in enumerate(events):
            match = 'data-id="%d"' % event.id
            if i >= 10 and i < 20:
                ok_(match in response.content, i)
            else:
                ok_(match not in response.content, i)

        output = response.content.decode('utf-8')
        ok_('href="%s"' % reverse('starred:home', args=(1,)) in output)
        ok_('href="%s"' % reverse('starred:home', args=(3,)) in output)

        response = self.client.get(url + 'page/3/')
        eq_(response.status_code, 200)

        for i, event in enumerate(events):
            match = 'data-id="%d"' % event.id
            if i >= 20:
                ok_(match in response.content, i)
            else:
                ok_(match not in response.content, i)

        output = response.content.decode('utf-8')
        ok_('href="%s"' % reverse('starred:home', args=(2,)) in output)
        ok_('href="%s"' % reverse('starred:home', args=(4,)) not in output)
