import datetime
from cStringIO import StringIO

import mock
from nose.tools import eq_, ok_

from django.core import mail
from django.conf import settings
from django.utils import timezone
from django.test.utils import override_settings
from django.core.urlresolvers import reverse

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.manage.archiver import archive
from airmozilla.main.models import Event, Template, VidlySubmission


SAMPLE_XML = (
    '<?xml version="1.0"?>'
    '<Response><Message>Action successful.</Message>'
    '<MessageCode>4.1</MessageCode><Success><Task><UserID>1234</UserID>'
    '<MediaShortLink>abc123</MediaShortLink>'
    '<SourceFile>http://videos.mozilla.org/bla.f4v</SourceFile>'
    '<BatchID>35402</BatchID>'
    '<Status>Finished</Status>'
    '<Private>false</Private>'
    '<PrivateCDN>false</PrivateCDN><Created>2012-08-23 19:30:58</Created>'
    '<Updated>2012-08-23 20:44:22</Updated>'
    '<UserEmail>airmozilla@mozilla.com</UserEmail>'
    '</Task></Success></Response>'
)

SAMPLE_MEDIALIST_XML = (
    '<?xml version="1.0"?>'
    '<Response><Message>OK</Message><MessageCode>7.4</MessageCode><Success>'
    '<Media><MediaShortLink>abc123</MediaShortLink><VanityLink/>'
    '<Notify>vvm@spb-team.com</Notify><Created>2011-12-25 18:45:56</Created>'
    '<Updated>2012-11-28 14:05:07</Updated><Status>Finished</Status>'
    '<IsDeleted>false</IsDeleted><IsPrivate>false</IsPrivate>'
    '<IsPrivateCDN>false</IsPrivateCDN><CDN>AWS</CDN></Media>'
    '<Media><MediaShortLink>xyz987</MediaShortLink><VanityLink/>'
    '<Notify>vvm@spb-team.com</Notify><Created>2011-12-25 19:41:05</Created>'
    '<Updated>2012-11-28 14:04:57</Updated><Status>Error</Status>'
    '<IsDeleted>false</IsDeleted><IsPrivate>false</IsPrivate>'
    '<IsPrivateCDN>false</IsPrivateCDN><CDN>AWS</CDN></Media>'
    '</Success></Response>'
)


class ArchiverTestCase(DjangoTestCase):

    def _age_event_created(self, event, save=True):
        extra_seconds = settings.PESTER_INTERVAL_DAYS * 24 * 60 * 60 + 1
        now = timezone.now()
        event.created = now - datetime.timedelta(seconds=extra_seconds)
        save and event.save()

    @mock.patch('airmozilla.manage.archiver.logging')
    def test_a_bad_event_parameter_1(self, mocked_logging):
        event = Event.objects.get(title='Test event')
        archive(event)
        mocked_logging.warn.assert_called_with(
            'Event %r not a Vid.ly event', 'Test event'
        )

    @mock.patch('airmozilla.manage.archiver.logging')
    def test_a_bad_event_parameter_2(self, mocked_logging):
        event = Event.objects.get(title='Test event')
        vidly_template = Template.objects.create(name='Vid.ly Test')
        event.template = vidly_template
        event.save()
        archive(event)
        mocked_logging.warn.assert_called_with(
            'Event %r does not have a Vid.ly tag', u'Test event'
        )

    @override_settings(ADMINS=(('F', 'foo@bar.com'), ('B', 'bar@foo.com')))
    @mock.patch('urllib2.urlopen')
    def test_still_not_found(self, p_urlopen):

        def mocked_urlopen(request):
            return StringIO(SAMPLE_MEDIALIST_XML.strip())

        p_urlopen.side_effect = mocked_urlopen

        event = Event.objects.get(title='Test event')
        vidly_template = Template.objects.create(name='Vid.ly Test')
        event.template = vidly_template
        event.template_environment = {'tag': 'NOTKNOWN'}
        event.save()
        archive(event)

        sent_email = mail.outbox[-1]
        eq_(sent_email.to, [x[1] for x in settings.ADMINS])
        ok_('NOTKNOWN' in sent_email.subject)
        ok_(reverse('manage:event_edit', args=(event.pk,)) in sent_email.body)

    @override_settings(ADMINS=(('F', 'foo@bar.com'), ('B', 'bar@foo.com')))
    @mock.patch('urllib2.urlopen')
    def test_errored(self, p_urlopen):

        def mocked_urlopen(request):
            xml = SAMPLE_XML.replace(
                '<Status>Finished</Status>',
                '<Status>Error</Status>',
            )
            return StringIO(xml.strip())

        p_urlopen.side_effect = mocked_urlopen

        event = Event.objects.get(title='Test event')
        vidly_template = Template.objects.create(name='Vid.ly Test')
        event.template = vidly_template
        event.template_environment = {'tag': 'abc123'}
        event.save()
        archive(event)

        sent_email = mail.outbox[-1]
        eq_(sent_email.to, [x[1] for x in settings.ADMINS])
        ok_('Unable to archive event' in sent_email.subject)
        ok_('abc123' in sent_email.subject)
        ok_(reverse('manage:event_edit', args=(event.pk,)) in sent_email.body)

    @override_settings(ADMINS=(('F', 'foo@bar.com'),))
    @mock.patch('urllib2.urlopen')
    def test_errored_updating_vidly_submission(self, p_urlopen):

        def mocked_urlopen(request):
            xml = SAMPLE_XML.replace(
                '<Status>Finished</Status>',
                '<Status>Error</Status>',
            )
            return StringIO(xml.strip())

        p_urlopen.side_effect = mocked_urlopen

        event = Event.objects.get(title='Test event')
        vidly_template = Template.objects.create(name='Vid.ly Test')
        event.template = vidly_template
        event.template_environment = {'tag': 'abc123'}
        event.save()
        vidly_submission = VidlySubmission.objects.create(
            event=event,
            url='https://example.com',
            tag='abc123'
        )
        archive(event)

        vidly_submission = VidlySubmission.objects.get(id=vidly_submission.id)
        ok_(vidly_submission.errored)
        ok_(not vidly_submission.finished)

    @mock.patch('urllib2.urlopen')
    def test_processing(self, p_urlopen):

        def mocked_urlopen(request):
            xml = SAMPLE_XML.replace(
                '<Status>Finished</Status>',
                '<Status>Processing</Status>',
            )
            return StringIO(xml.strip())

        p_urlopen.side_effect = mocked_urlopen

        event = Event.objects.get(title='Test event')
        vidly_template = Template.objects.create(name='Vid.ly Test')
        event.template = vidly_template
        event.template_environment = {'tag': 'abc123'}
        event.save()
        archive(event)

        eq_(len(mail.outbox), 0)

    @mock.patch('urllib2.urlopen')
    def test_finished(self, p_urlopen):

        def mocked_urlopen(request):
            return StringIO(SAMPLE_XML.strip())

        p_urlopen.side_effect = mocked_urlopen

        event = Event.objects.get(title='Test event')
        event.status = Event.STATUS_PENDING
        event.archive_time = None
        vidly_template = Template.objects.create(name='Vid.ly Test')
        event.template = vidly_template
        event.template_environment = {'tag': 'abc123'}
        event.save()
        archive(event)

        eq_(len(mail.outbox), 0)

        event = Event.objects.get(pk=event.pk)
        now = timezone.now()
        eq_(
            event.archive_time.strftime('%Y%m%d %H%M'),
            now.strftime('%Y%m%d %H%M'),
        )
        eq_(event.status, Event.STATUS_SCHEDULED)

    @mock.patch('urllib2.urlopen')
    def test_finished_updating_vidly_submission(self, p_urlopen):

        def mocked_urlopen(request):
            return StringIO(SAMPLE_XML.strip())

        p_urlopen.side_effect = mocked_urlopen

        event = Event.objects.get(title='Test event')
        event.status = Event.STATUS_PENDING
        event.archive_time = None
        vidly_template = Template.objects.create(name='Vid.ly Test')
        event.template = vidly_template
        event.template_environment = {'tag': 'abc123'}
        event.save()
        vidly_submission = VidlySubmission.objects.create(
            event=event,
            url='https://example.com',
            tag='abc123'
        )
        archive(event)

        vidly_submission = VidlySubmission.objects.get(id=vidly_submission.id)
        ok_(not vidly_submission.errored)
        ok_(vidly_submission.finished)
