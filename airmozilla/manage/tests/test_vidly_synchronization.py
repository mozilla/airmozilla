from cStringIO import StringIO
from nose.tools import ok_
import mock

# from django.test import TestCase
from airmozilla.main.models import Event, VidlySubmission
from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.manage import vidly_synchronization
from airmozilla.manage.tests.test_vidly import get_custom_XML


class TestVidlySynchronization(DjangoTestCase):

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_synchronize_all_correct_token_protection(self, p_urllib2):
        # If a VidlySubmission is token_protected by belongs to
        # a public event, and the actual video doesn't actually
        # isn't private (because it could have been manually changed
        # on the Vid.ly control panel).
        event = Event.objects.get(title='Test event')
        event.template.name = 'Vid.ly HD'
        event.template.save()
        assert event.privacy == Event.PRIVACY_PUBLIC

        submission = VidlySubmission.objects.create(
            event=event,
            tag='abc123',
            token_protection=True
        )

        def mocked_urlopen(request):
            return StringIO(
                get_custom_XML(
                    tag='abc123',
                    private='false'
                )
            )

        p_urllib2.urlopen = mocked_urlopen

        vidly_synchronization.synchronize_all()

        submission = VidlySubmission.objects.get(id=submission.id)
        ok_(not submission.token_protection)

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_synchronize_all_create_missing_submissions(self, p_urllib2):
        event = Event.objects.get(title='Test event')
        event.template.name = 'Vid.ly SD+HD'
        event.template.save()
        event.template_environment = {
            'tag': 'abc123',
            'other': 'junk',
        }
        event.save()

        assert not VidlySubmission.objects.filter(event=event)
        # create a bogus one
        VidlySubmission.objects.create(
            event=event,
            tag='xxx999',
        )

        def mocked_urlopen(request):
            return StringIO(
                get_custom_XML(
                    tag='abc123',
                    private='false',
                    hd='true',
                    user_email='foo@example.com',
                    source_file='https://cdn.example.com/file.flv',
                )
            )

        p_urllib2.urlopen = mocked_urlopen

        vidly_synchronization.synchronize_all()

        ok_(VidlySubmission.objects.get(
            event=event,
            tag='abc123',
            hd=True,
            token_protection=False,
            url='https://cdn.example.com/file.flv',
            email='foo@example.com'
        ))
