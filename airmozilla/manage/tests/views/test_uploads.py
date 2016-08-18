import mock
from nose.tools import eq_, ok_

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from airmozilla.main.models import Event, VidlySubmission
from airmozilla.uploads.models import Upload
from .base import ManageTestCase


class TestUploads(ManageTestCase):

    def test_uploads(self):
        user, = User.objects.all()[:1]
        Upload.objects.create(
            user=user,
            url='https://uploads.s3.amazonaws.com/2015/05/04/193226.mov',
            size=123456,
            mime_type='video/quicktime',
        )

        event = Event.objects.get(title='Test event')
        Upload.objects.create(
            event=event,
            user=user,
            url='https://uploads.s3.amazonaws.com/2015/05/04/2.mov',
            size=887766,
            mime_type='video/webm',
            upload_time=45
        )

        response = self.client.get(reverse('manage:uploads'))
        eq_(response.status_code, 200)
        ok_('<em>No event</em>' in response.content)
        event_edit_url = reverse('manage:event_edit', args=(event.id,))
        ok_(event_edit_url in response.content)

    def test_uploads_by_event(self):
        user, = User.objects.all()[:1]
        Upload.objects.create(
            user=user,
            url='https://uploads.s3.amazonaws.com/2015/05/04/193226.mov',
            size=123456,
            mime_type='video/quicktime',
        )

        event = Event.objects.get(title='Test event')
        Upload.objects.create(
            event=event,
            user=user,
            url='https://uploads.s3.amazonaws.com/event.mov',
            size=887766,
            mime_type='video/webm',
            upload_time=45
        )

        other_event = Event.objects.create(
            status=event.status,
            title='Other Title',
            slug='other',
            start_time=event.start_time,
            description='Something',
        )
        Upload.objects.create(
            event=other_event,
            user=user,
            url='https://uploads.s3.amazonaws.com/other.mov',
            size=1000,
            mime_type='video/mpeg',
            upload_time=60
        )

        url = reverse('manage:uploads')
        response = self.client.get(url, {'event': 9999})
        eq_(response.status_code, 404)
        response = self.client.get(url, {'event': event.id})
        eq_(response.status_code, 200)
        ok_('event.mov' in response.content)
        ok_('other.mov' not in response.content)

    @mock.patch('boto.connect_s3')
    def test_delete_uploads(self, mocked_connect_s3):
        event = Event.objects.get(title='Test event')
        upload1 = Upload.objects.create(
            event=event,
            user=self.user,
            url='https://uploads.s3.amazonaws.com/2015/05/04/2.mov',
            size=888,
            mime_type='video/webm',
            upload_time=45
        )
        upload2 = Upload.objects.create(
            event=event,
            user=self.user,
            url='https://uploads.s3.amazonaws.com/2015/05/04/3.mov',
            size=777,
            mime_type='video/webm',
            upload_time=54
        )
        VidlySubmission.objects.create(
            event=event,
            url=upload2.url + '?nocopy',
            tag='abc123',
        )

        url = reverse('manage:uploads')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response = self.client.post(url, {
            'event': event.id,
            'ids': [upload1.id, upload2.id],
        })
        # upload2 can't be deleted because it's associated with a
        # VidlySubmission
        eq_(response.status_code, 400)

        response = self.client.post(url, {
            'event': event.id,
            'ids': [upload1.id],
        })
        eq_(response.status_code, 302)

        ok_(not Upload.objects.filter(size=888))
        ok_(Upload.objects.filter(size=777))

        mocked_connect_s3().get_bucket().delete_key.assert_called_once_with(
            '/2015/05/04/2.mov'
        )
