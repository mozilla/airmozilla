import os
import json
import shutil

import mock
from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse

from airmozilla.main.models import (
    Event,
    Chapter,
    Picture,
    Template,
)
from airmozilla.uploads.models import Upload
from airmozilla.base.tests.testbase import DjangoTestCase, Response


class TestEventEditChapters(DjangoTestCase):
    sample_jpg = 'airmozilla/manage/tests/presenting.jpg'

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

    @mock.patch('subprocess.Popen')
    def test_add_chapter(self, mock_popen):

        ffmpeged_urls = []

        sample_jpg = self.sample_jpg

        def mocked_popen(command, **kwargs):
            url = command[4]
            ffmpeged_urls.append(url)
            destination = command[-1]
            assert os.path.isdir(os.path.dirname(destination))

            class Inner:
                def communicate(self):
                    out = err = ''
                    if url == 'https://aws.com/file.mov':
                        shutil.copyfile(sample_jpg, destination)
                    else:
                        raise NotImplementedError(url)
                    return out, err

            return Inner()

        mock_popen.side_effect = mocked_popen

        url = reverse('main:event_edit_chapters', args=('xxx',))
        data = {
            'timestamp': 70,
            'text': ' Bla bla ',
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 404)

        event = Event.objects.get(title='Test event')
        event.upload = Upload.objects.create(
            user=event.creator,
            url='https://aws.com/file.mov',
            size=1234,
            mime_type='video/quicktime',
        )
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

    @mock.patch('requests.head')
    @mock.patch('subprocess.Popen')
    def test_fetch_thumbnails(self, mock_popen, rhead):

        def mocked_head(url, **options):
            return Response(
                '',
                200
            )

        rhead.side_effect = mocked_head

        ffmpeged_urls = []

        sample_jpg = self.sample_jpg

        def mocked_popen(command, **kwargs):
            url = command[4]
            ffmpeged_urls.append(url)
            destination = command[-1]
            assert os.path.isdir(os.path.dirname(destination))

            class Inner:
                def communicate(self):
                    out = err = ''
                    if 'xyz123' in url:
                        shutil.copyfile(sample_jpg, destination)
                    else:
                        raise NotImplementedError(url)
                    return out, err

            return Inner()

        mock_popen.side_effect = mocked_popen

        url = reverse('main:event_chapters_thumbnails', args=('xxx',))
        response = self.client.get(url)
        eq_(response.status_code, 404)

        event = Event.objects.get(title='Test event')
        event.duration = 35
        event.privacy = Event.PRIVACY_COMPANY
        template = Template.objects.create(
            name='Vid.ly Something',
            content="{{ tag }}"
        )
        event.template = template
        event.template_environment = {'tag': 'xyz123'}
        event.save()
        url = reverse('main:event_chapters_thumbnails', args=(event.slug,))
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
        eq_(json.loads(response.content), {'pictures': [], 'missing': 6})
        qs = Picture.objects.filter(
            event=event,
            timestamp__isnull=False
        )
        eq_(qs.count(), 6)
        timestamps = [x.timestamp for x in qs.order_by('timestamp')]
        eq_(timestamps, [5, 10, 15, 20, 25, 30])

        # call it again
        response = self.client.get(url)
        # finally!
        eq_(response.status_code, 200)
        struct = json.loads(response.content)
        eq_(struct['missing'], 0)
        eq_(len(struct['pictures']), 6)

    def test_no_chapter_edit_unless_scheduled(self):
        event = Event.objects.get(title='Test event')
        assert event.is_scheduled()
        # Set a template so it can have chapters
        template = Template.objects.create(
            name='Vid.ly Something',
            content="{{ tag }}"
        )
        event.template = template
        event.template_environment = {'tag': 'xyz123'}
        event.save()
        # And we need to log in
        self._login()

        url = reverse('main:event_edit_chapters', args=(event.slug,))
        view_url = reverse('main:event', args=(event.slug,))
        response = self.client.get(view_url)
        eq_(response.status_code, 200)
        ok_('Edit chapters' in response.content.decode('utf-8'))
        ok_(url in response.content.decode('utf-8'))
        # And we can now even open it and start editing the chapters
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # However, if the event is no longer scheduled, you should not
        # be able to edit chapters.
        event.status = Event.STATUS_PROCESSING
        event.save()

        # but if the event is processing,
        response = self.client.get(view_url)
        eq_(response.status_code, 200)
        ok_('Edit chapters' not in response.content.decode('utf-8'))
        ok_(url not in response.content.decode('utf-8'))

        response = self.client.get(url)
        eq_(response.status_code, 302)
        ok_(response['Location'].endswith(view_url))
