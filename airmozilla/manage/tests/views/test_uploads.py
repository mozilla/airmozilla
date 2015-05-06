from nose.tools import eq_, ok_

from django.contrib.auth.models import User
from funfactory.urlresolvers import reverse

from airmozilla.main.models import Event
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

    # def test_loggedsearches_stats(self):
    #     # Deliberately kept very simply because it'sa superuser-only feature
    #     # and its use is very minimal.
    #     response = self.client.get(reverse('manage:loggedsearches_stats'))
    #     eq_(response.status_code, 200)
