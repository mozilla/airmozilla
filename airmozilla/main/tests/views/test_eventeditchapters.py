import json

from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse

from airmozilla.main.models import (
    Event,
    Chapter,
)
from airmozilla.base.tests.testbase import DjangoTestCase


class TestEventEditChapters(DjangoTestCase):

    def test_view(self):
        url = reverse('main:event_edit_chapters', args=('xxx',))
        response = self.client.get(url)
        eq_(response.status_code, 404)

        event = Event.objects.get(title='Test event')
        event.privacy = Event.PRIVACY_COMPANY
        event.save()
        url = reverse('main:event_edit_chapters', args=(event.slug,))
        response = self.client.get(url)
        # because it's not a public event
        eq_(response.status_code, 302)

        # make it public again
        event.privacy = Event.PRIVACY_PUBLIC
        event.save()
        response = self.client.get(url)
        # because you're not signed in
        eq_(response.status_code, 302)

        self._login()
        response = self.client.get(url)
        # finally!
        eq_(response.status_code, 200)

    def test_get_chapters_json(self):
        event = Event.objects.get(title='Test event')
        event.privacy = Event.PRIVACY_COMPANY
        event.save()
        user = self._login()
        url = reverse('main:event_edit_chapters', args=(event.slug,))
        response = self.client.get(url, {'all': True})
        eq_(response.status_code, 200)
        chapters = json.loads(response.content)['chapters']
        eq_(chapters, [])

        Chapter.objects.create(
            event=event,
            timestamp=70,
            text='Some text',
            user=user,
        )
        response = self.client.get(url, {'all': True})
        eq_(response.status_code, 200)
        ok_('max-age=0' in response['Cache-Control'])
        chapters = json.loads(response.content)['chapters']
        chapter, = chapters
        eq_(chapter['timestamp'], 70)
        eq_(chapter['text'], 'Some text')
        eq_(chapter['user'], {
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
        })

    def test_add_chapter(self):
        url = reverse('main:event_edit_chapters', args=('xxx',))
        data = {
            'timestamp': 70,
            'text': ' Bla bla ',
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 404)

        event = Event.objects.get(title='Test event')
        event.privacy = Event.PRIVACY_COMPANY
        event.save()
        url = reverse('main:event_edit_chapters', args=(event.slug,))
        response = self.client.post(url, data)
        # because it's not a public event
        eq_(response.status_code, 302)

        # make it public again
        event.privacy = Event.PRIVACY_PUBLIC
        event.save()
        response = self.client.post(url, data)
        # because you're not signed in
        eq_(response.status_code, 302)

        self._login()
        response = self.client.post(url, data)
        # finally!
        eq_(response.status_code, 200)
        # sort, of
        ok_(json.loads(response.content)['errors']['timestamp'])

        event.duration = 90
        event.save()
        response = self.client.post(url, data)
        # finally!
        eq_(response.status_code, 200)
        # sort, of
        ok_(json.loads(response.content)['ok'])

        assert Chapter.objects.filter(event=event).count() == 1
        chapter = Chapter.objects.get(event=event, timestamp=70)
        eq_(chapter.text, 'Bla bla')

        # make an edit
        data['text'] = 'Different text'
        response = self.client.post(url, data)
        # finally!
        eq_(response.status_code, 200)
        # sort, of
        ok_(json.loads(response.content)['ok'])
        assert Chapter.objects.filter(event=event).count() == 1
        chapter = Chapter.objects.get(id=chapter.id)
        eq_(chapter.text, 'Different text')

        # now delete it
        data['delete'] = True
        response = self.client.post(url, data)
        eq_(response.status_code, 200)
        ok_(json.loads(response.content)['ok'])
        ok_(not Chapter.objects.filter(event=event, is_active=True).exists())
