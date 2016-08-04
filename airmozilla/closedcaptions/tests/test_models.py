import os

from nose.tools import ok_

from django.core.files import File

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.closedcaptions.models import ClosedCaptions
from airmozilla.main.models import Event

from .test_views import TEST_DIRECTORY


class ClosedCaptionsTestCase(DjangoTestCase):

    def test_set_transcript_from_file(self):
        event = Event.objects.get(title='Test event')
        filepath = os.path.join(TEST_DIRECTORY, 'example.dfxp')
        with open(filepath) as f:
            cc = ClosedCaptions.objects.create(
                event=event,
                file=File(f),
            )
        cc.set_transcript_from_file()
        ok_(cc.transcript)
        ok_(cc.transcript['subtitles'])

    def test_get_plaintext_transcript(self):
        event = Event.objects.get(title='Test event')
        filepath = os.path.join(TEST_DIRECTORY, 'example.dfxp')
        with open(filepath) as f:
            cc = ClosedCaptions.objects.create(
                event=event,
                file=File(f),
            )
        text = cc.get_plaintext_transcript()
        ok_(text)
        ok_(text.startswith(u'Ping'))
