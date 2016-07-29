import os

from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse

from airmozilla.main.models import Event
from airmozilla.closedcaptions.models import ClosedCaptions
from .base import ManageTestCase
from airmozilla.closedcaptions.tests.test_views import TEST_DIRECTORY


class TestClosedCaptions(ManageTestCase):

    def test_upload_closed_captions(self):
        event = Event.objects.get(title='Test event')
        url = reverse('manage:event_closed_captions', args=(event.id,))

        # let's upload all sample files we have
        filenames = ('example.dfxp', 'example.srt')
        for filename in filenames:
            with open(os.path.join(TEST_DIRECTORY, filename)) as fp:
                response = self.client.post(url, {'file': fp})
                eq_(response.status_code, 302)

        eq_(
            ClosedCaptions.objects.filter(event=event).count(),
            len(filenames)
        )

        # Render the page now that there's content in there
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # some incompatible file
        filepath = os.path.join(TEST_DIRECTORY, 'test_views.py')
        with open(filepath) as fp:
            response = self.client.post(url, {'file': fp})
            eq_(response.status_code, 200)
            ok_(
                'Not a valid caption file that could be recognized' in
                response.content
            )

        # lastly delete the example.srt one
        item, = [
            x for x in ClosedCaptions.objects.filter(event=event)
            if x.file_info['name'] == 'example.srt'
        ]
        url = reverse('manage:event_closed_captions_delete', args=(
            event.id,
            item.id,
        ))
        response = self.client.post(url)
        eq_(response.status_code, 302)
        eq_(
            ClosedCaptions.objects.filter(event=event).count(),
            len(filenames) - 1
        )
