from nose.tools import eq_, ok_

from django.contrib.auth.models import Group, Permission
from django.db.models import Q
from django.core.urlresolvers import reverse

from airmozilla.main.models import Event, Chapter
from .base import ManageTestCase


class TestEventChapters(ManageTestCase):

    def setUp(self):
        super(TestEventChapters, self).setUp()
        self.user.is_superuser = False
        self.user.is_staff = True
        self.user.save()

        # now let's give this user the relevant permissions
        producers = Group.objects.create(name='Producer')
        self.user.groups.add(producers)
        # and we grant a couple of relevant permissions to this group
        permissions = Permission.objects.filter(
            Q(codename='add_chapter') |
            Q(codename='change_chapter') |
            Q(codename='delete_chapter')
        )
        for permission in permissions:
            producers.permissions.add(permission)

    def test_chapters(self):
        event = Event.objects.get(title='Test event')
        response = self.client.get(
            reverse('manage:event_chapters', args=(event.id,))
        )
        eq_(response.status_code, 200)

    def test_event_chapter_new(self):
        event = Event.objects.get(title='Test event')
        url = reverse('manage:event_chapter_new', args=(event.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response = self.client.post(url, {
            'text': 'The conclusion',
            'timestamp': '13m20s',
        })
        self.assertRedirects(
            response, reverse('manage:event_chapters', args=(event.id,))
        )
        ok_(Chapter.objects.get(
            text='The conclusion',
            timestamp=13 * 60 + 20
        ))
        response_fail = self.client.post(url)
        eq_(response_fail.status_code, 200)

    def test_event_chapter_edit(self):
        event = Event.objects.get(title='Test event')
        chapter = Chapter.objects.create(
            event=event,
            user=self.user,
            text='The Q&A Session',
            timestamp=70
        )
        url = reverse(
            'manage:event_chapter_edit',
            args=(event.id, chapter.id,)
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('1m10s' in response.content)

        response = self.client.post(url, {
            'text': 'Other Text',
            'timestamp': '1h 1m 1s'
        })
        self.assertRedirects(
            response,
            reverse('manage:event_chapters', args=(event.id,))
        )
        chapter = Chapter.objects.get(id=chapter.id)
        eq_(chapter.text, 'Other Text')
        eq_(chapter.timestamp, 60 * 60 + 60 + 1)
        response_fail = self.client.post(url, {
            'text': 'Web Developer',
            'timestamp': ''
        })
        eq_(response_fail.status_code, 200)

        event.duration = 100
        event.save()
        response_fail = self.client.post(url, {
            'text': 'Web Developer',
            'timestamp': '2m'  # 2m > 100 seconds
        })
        eq_(response_fail.status_code, 200)

    def test_event_chapter_delete(self):
        event = Event.objects.get(title='Test event')
        chapter = Chapter.objects.create(
            event=event,
            user=self.user,
            text='Web Developer',
            timestamp=70
        )
        url = reverse(
            'manage:event_chapter_delete',
            args=(event.id, chapter.id)
        )
        response = self.client.post(url)
        eq_(response.status_code, 302)
        url = reverse('manage:event_chapters', args=(event.id,))
        ok_(url in response['Location'])
