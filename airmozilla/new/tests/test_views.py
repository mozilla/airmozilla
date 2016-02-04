# -*- coding: utf-8 -*-
import os
import re
import json
import urllib
import shutil
import datetime
from cStringIO import StringIO

import mock
from nose.tools import eq_, ok_
from PIL import Image

from django.contrib.auth.models import Group, Permission, User
from django.conf import settings
from django.core.files import File
from django.utils import timezone
from django.core import mail
from django.core.urlresolvers import reverse

from airmozilla.base.tests.testbase import DjangoTestCase, Response
from airmozilla.main.models import (
    Event,
    VidlySubmission,
    Template,
    Picture,
    Tag,
    Channel,
    Approval,
    Topic,
)
from airmozilla.uploads.models import Upload
from airmozilla.manage.tests.views.test_vidlymedia import (
    get_custom_XML,
    SAMPLE_MEDIA_RESULT_SUCCESS
)


def almost_eq_(one, two, delta):
    if isinstance(delta, int):
        ok_(abs(one - two) <= delta, '%r !~= %r' % (one, two))
    else:
        raise NotImplementedError(delta)


class TestNew(DjangoTestCase):
    sample_jpg = 'airmozilla/manage/tests/presenting.jpg'

    def _create_event(self, file_url=None, user=None):
        file_url = file_url or 'https://s3.com/foo.webm'
        user = user or self._login()
        url = reverse('new:save_upload')
        data = {
            'url': file_url,
            'mime_type': 'video/webm',
            'file_name': 'bar.webm',
            'size': 12345678
        }
        response = self.post_json(url, data)
        assert response.status_code == 200, response.status_code
        event = Upload.objects.get(url=file_url).event
        assert event.upload
        return event

    def _create_youtube_event(self, id=None, user=None):
        user = user or self._login()
        event = Event.objects.create(
            creator=user,
            title='Automatically Set',
            template_environment={'id': id},
            start_time=timezone.now(),
            archive_time=timezone.now(),
            status=Event.STATUS_INITIATED,
        )
        template, __ = Template.objects.get_or_create(
            name='YouTube',
            content='<iframe src="//youtube.com/{{id}}"></iframe>'
        )
        event.template = template
        event.save()
        self._attach_file(event, self.sample_jpg)

        parent, __ = Channel.objects.get_or_create(
            name='YouTube',
            slug='youtube'
        )
        channel, __ = Channel.objects.get_or_create(
            parent=parent,
            name='PyCon 2019',
            slug='pycon-2019',
            youtube_id='x1c2v3b4n5m6'
        )
        return event

    def _create_default_archive_template(self):
        try:
            return Template.objects.get(default_archive_template=True)
        except Template.DoesNotExist:
            return Template.objects.create(
                name='Vid.ly Default',
                default_archive_template=True,
                content='<script src="{{ tag}}"></script>'
            )

    def _create_youtube_template(self):
        try:
            return Template.objects.get(name='YouTube')
        except Template.DoesNotExist:
            return Template.objects.create(
                name='YouTube',
                content=(
                    '<iframe src="//youtube.com/{{id}}"></iframe>'
                )
            )

    def _create_approval_group(self):
        group = Group.objects.create(name='PR Group')
        group.permissions.add(
            Permission.objects.get(codename='change_approval')
        )
        jessica = User.objects.create(
            username='jessica',
            email='jessica@example.com'
        )
        jessica.groups.add(group)
        return group, [jessica]

    def test_home(self):
        response = self.client.get(reverse('new:home'))
        eq_(response.status_code, 302)
        self._login()
        response = self.client.get(reverse('new:home'))
        eq_(response.status_code, 200)
        # the only thing special is that you shouldn't see the sidebar
        ok_('id="content-sub"' not in response.content)

    def test_save_upload(self):
        # basics first
        url = reverse('new:save_upload')
        data = {
            'url': 'https://s3.com/foo.webm',
            'mime_type': 'video/webm',
            'file_name': 'bar.webm',
            'size': 12345678,
            'upload_time': '123',
        }
        response = self.post_json(url, data)
        eq_(response.status_code, 403)

        user = self._login()
        response = self.post_json(url, data)
        eq_(response.status_code, 200)
        # There should now we be an event with that id and it should be
        # associated with an upload.
        upload = Upload.objects.get(
            user=user,
            url=data['url'],
            mime_type=data['mime_type'],
            file_name=data['file_name'],
            size=data['size'],
            upload_time=int(data['upload_time']),
        )
        event, = Event.objects.filter(upload=upload)
        eq_(event.creator, user)
        eq_(event.id, json.loads(response.content)['id'])

    def test_save_upload_bad(self):
        self._login()
        url = reverse('new:save_upload')
        data = {
            'url': 'https://s3.com  :SPACES: /foo.webm',
            'mime_type': 'video/webm',
            'file_name': 'bar.webm',
            'size': 12345678
        }
        response = self.post_json(url, data)
        eq_(response.status_code, 400)

        data = {
            'url': 'https://s3.com/foo.webm',
            'mime_type': 'video/webm',
            'file_name': 'bar.webm',
            'size': 'not a number'
        }
        response = self.post_json(url, data)
        eq_(response.status_code, 400)

    def test_render_partial_templates(self):
        url = reverse(
            'new:partial_template',
            args=('picture.html',)
        )
        response = self.client.get(url)
        eq_(response.status_code, 403)
        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('</html>' not in response.content)

        # the details.html one contains a form
        url = reverse(
            'new:partial_template',
            args=('details.html',)
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('id="details-form"' in response.content)

        # some junk
        url = reverse(
            'new:partial_template',
            args=('junk.html',)
        )
        response = self.client.get(url)
        eq_(response.status_code, 404)

    def test_render_edit_template(self):
        # make one channel that is always shown
        great_channel = Channel.objects.create(
            name='Great', slug='great', always_show=True
        )
        poor_channel = Channel.objects.create(
            name='Poor', slug='poor'
        )
        bad_channel = Channel.objects.create(
            name='Bad', slug='bad', never_show=True
        )
        topic1 = Topic.objects.create(topic='Topic 1')
        topicX = Topic.objects.create(topic='Topic X', is_active=False)
        self._login()
        url = reverse(
            'new:partial_template',
            args=('details.html',)
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # channels that are always on are shown before the "Show more"
        html_before = response.content.split('Show more')[0]
        html_after = response.content.split('Show more')[1]

        html = 'name="channel" value="{0}"'.format(great_channel.id)
        ok_(html in html_before)
        ok_(html not in html_after)

        html = 'name="channel" value="{0}"'.format(poor_channel.id)
        ok_(html not in html_before)
        ok_(html in html_after)

        html = 'name="channel" value="{0}"'.format(bad_channel.id)
        ok_(html not in html_before)
        ok_(html not in html_after)

        ok_(
            'ng-model="event.topics[&quot;%s&quot;]"' % topic1.id
            in response.content
        )
        ok_(
            'ng-model="event.topics[&quot;%s&quot;]"' % topicX.id
            not in response.content
        )

    def test_edit(self):
        event = Event.objects.get(title='Test event')
        url = reverse('new:edit', args=(event.id,))
        channel1 = Channel.objects.create(name='Channel 1', slug='channel1')
        channel2 = Channel.objects.create(name='Channel 2', slug='channel2')
        topic1 = Topic.objects.create(topic='Topic 1')
        topic2 = Topic.objects.create(topic='Topic 2')
        data = {
            'title': 'New Title  ',
            'description': 'My Description',
            'privacy': Event.PRIVACY_CONTRIBUTORS,
            'tags': ' one, two, ',
            'channels': {
                channel1.id: False,
                channel2.id: True,
            },
            'topics': {
                topic1.id: False,
                topic2.id: True,
            }
        }
        response = self.post_json(url, data)
        eq_(response.status_code, 403)

        user = self._login()
        response = self.post_json(url, data)
        # not yours to edit
        eq_(response.status_code, 403)
        event.creator = user
        event.save()

        assert event.status == Event.STATUS_SCHEDULED
        response = self.post_json(url, data)
        # event is scheduled
        eq_(response.status_code, 400)

        event.status = Event.STATUS_INITIATED
        event.save()
        response = self.post_json(url, data)
        # finally!
        eq_(response.status_code, 200)
        event = Event.objects.get(title=data['title'].strip())
        eq_(event.slug, 'new-title')
        event_data = json.loads(response.content)['event']
        eq_(event_data['title'], event.title)
        eq_(event_data['description'], event.description)
        eq_(event_data['privacy'], Event.PRIVACY_CONTRIBUTORS)
        tags = list(event.tags.all())
        eq_(len(tags), 2)
        ok_(Tag.objects.get(name='one') in tags)
        ok_(Tag.objects.get(name='two') in tags)
        eq_(list(event.channels.all()), [channel2])
        eq_(list(event.topics.all()), [topic2])

    def test_edit_errors(self):
        event = self._create_event()
        url = reverse('new:edit', args=(event.id,))
        data = {
            'title': '  ',
            'description': '',
            'privacy': 'junk',
            'tags': ' one, two, '
        }
        response = self.post_json(url, data)
        eq_(response.status_code, 200)
        errors = json.loads(response.content)['errors']
        ok_(errors['title'])
        ok_(errors['description'])
        ok_(errors['privacy'])
        # XXX channel?

    def test_edit_same_title_different_slug(self):
        event = Event.objects.get(title='Test event')
        assert event.slug == 'test-event'

        event = self._create_event()
        url = reverse('new:edit', args=(event.id,))
        data = {
            'title': 'TEST EVENT',
            'description': 'Other Description',
            'privacy': Event.PRIVACY_CONTRIBUTORS,
        }
        response = self.post_json(url, data)
        eq_(response.status_code, 200)
        event = Event.objects.get(id=event.id)
        eq_(event.slug, 'test-event-' + timezone.now().strftime('%Y%m%d'))

        # a second time
        data['description'] = 'Different this time'
        response = self.post_json(url, data)
        eq_(response.status_code, 200)
        previous_slug = event.slug
        event = Event.objects.get(id=event.id)
        eq_(event.slug, previous_slug)

        # but now really change it
        data['title'] = 'Ölen smälter i åsen'
        response = self.post_json(url, data)
        eq_(response.status_code, 200)
        event = Event.objects.get(id=event.id)
        eq_(event.slug, 'olen-smalter-i-asen')

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_archive(self, p_urllib2):

        self._create_default_archive_template()

        def mocked_urlopen(request):
            return StringIO("""
            <?xml version="1.0"?>
            <Response>
              <Message>All medias have been added.</Message>
              <MessageCode>2.1</MessageCode>
              <BatchID>47520</BatchID>
              <Success>
                <MediaShortLink>
                  <SourceFile>http://www.com/file.flv</SourceFile>
                  <ShortLink>8oxv6x</ShortLink>
                  <MediaID>13969839</MediaID>
                  <QRCode>http://vid.ly/8oxv6x/qrcodeimg</QRCode>
                  <HtmlEmbed>code code</HtmlEmbed>
                  <EmailEmbed>more code code</EmailEmbed>
                </MediaShortLink>
              </Success>
            </Response>
            """)

        webhook_url = 'http://testserver' + reverse('new:vidly_media_webhook')

        file_url = 'https://s3.com/foo.webm'

        addmedia_requests = []

        def make_mock_request(url, querystring):
            xml_qs = urllib.unquote(querystring)
            addmedia_requests.append(xml_qs)
            return mock.MagicMock()

        p_urllib2.Request.side_effect = make_mock_request
        p_urllib2.urlopen = mocked_urlopen

        event = self._create_event(file_url)

        url = reverse('new:archive', args=(event.id,))
        response = self.post_json(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), {
            'tag': '8oxv6x',
            'error': None,
        })

        xml_qs, = addmedia_requests
        ok_('<SourceFile>{0}</SourceFile>'.format(file_url) in xml_qs)
        ok_('<Notify>{0}</Notify>'.format(webhook_url) in xml_qs)

        submission, = VidlySubmission.objects.filter(event=event)
        eq_(submission.url, file_url)

        # hit a second time and that shouldn't create any new submissions
        response = self.post_json(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), {
            'tag': '8oxv6x',
            'error': None,
        })
        eq_(VidlySubmission.objects.filter(event=event).count(), 1)
        eq_(len(addmedia_requests), 1)

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_archive_with_s3_url(self, p_urllib2):

        self._create_default_archive_template()

        def mocked_urlopen(request):
            return StringIO("""
            <?xml version="1.0"?>
            <Response>
              <Message>All medias have been added.</Message>
              <MessageCode>2.1</MessageCode>
              <BatchID>47520</BatchID>
              <Success>
                <MediaShortLink>
                  <SourceFile>http://www.com/file.flv</SourceFile>
                  <ShortLink>8oxv6x</ShortLink>
                  <MediaID>13969839</MediaID>
                  <QRCode>http://vid.ly/8oxv6x/qrcodeimg</QRCode>
                  <HtmlEmbed>code code</HtmlEmbed>
                  <EmailEmbed>more code code</EmailEmbed>
                </MediaShortLink>
              </Success>
            </Response>
            """)

        webhook_url = 'http://testserver' + reverse('new:vidly_media_webhook')

        file_url = 'https://air-mozilla-uploads.s3.amazonaws.com/foo.mov'

        addmedia_requests = []

        def make_mock_request(url, querystring):
            xml_qs = urllib.unquote(querystring)
            addmedia_requests.append(xml_qs)
            return mock.MagicMock()

        p_urllib2.Request.side_effect = make_mock_request
        p_urllib2.urlopen = mocked_urlopen

        event = self._create_event(file_url)

        url = reverse('new:archive', args=(event.id,))
        response = self.post_json(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), {
            'tag': '8oxv6x',
            'error': None,
        })
        xml_qs, = addmedia_requests
        ok_(
            '<SourceFile>{0}</SourceFile>'.format(file_url + '?nocopy')
            in xml_qs
        )
        ok_('<Notify>{0}</Notify>'.format(webhook_url) in xml_qs)

        submission, = VidlySubmission.objects.filter(event=event)
        eq_(submission.url, file_url + '?nocopy')

        # run it a second time
        response = self.post_json(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), {
            'tag': '8oxv6x',
            'error': None,
        })
        eq_(len(addmedia_requests), 1)

    def test_archive_pending_event(self):
        event = self._create_event()
        event.status = Event.STATUS_PENDING
        event.save()

        url = reverse('new:archive', args=(event.id,))
        response = self.post_json(url)
        eq_(response.status_code, 400)

    def test_screencaptures_pending_event(self):
        event = self._create_event()
        event.status = Event.STATUS_PENDING
        event.save()

        url = reverse('new:screencaptures', args=(event.id,))
        response = self.post_json(url)
        eq_(response.status_code, 400)

    @mock.patch('requests.head')
    @mock.patch('subprocess.Popen')
    def test_trigger_vidly_media_webhook(self, mock_popen, rhead):

        ffmpeged_urls = []

        def mocked_popen(command, **kwargs):
            url = destination = None
            if command[1] == '-i':
                # doing a fetch info
                url = command[2]
            elif command[1] == '-ss':
                # screen capturing
                destination = command[-1]
                assert os.path.isdir(os.path.dirname(destination))
            else:
                raise NotImplementedError(command)

            ffmpeged_urls.append(url)

            sample_jpg = self.sample_jpg

            class Inner:
                def communicate(self):
                    out = err = ''
                    if url is not None:
                        if 'abc123' in url:
                            err = """
                Duration: 00:19:17.47, start: 0.000000, bitrate: 1076 kb/s
                            """
                        else:
                            raise NotImplementedError(url)
                    elif destination is not None:
                        shutil.copyfile(sample_jpg, destination)
                    else:
                        raise NotImplementedError()
                    return out, err

            return Inner()

        mock_popen.side_effect = mocked_popen

        def mocked_head(url, **options):
            return Response(
                '',
                200
            )

        rhead.side_effect = mocked_head

        # the webhook is supposed to be sent back when the file has
        # been submitted and successfully transcoded.

        file_url = 'https://s3.com/foo.webm'
        event = self._create_event(file_url)

        tag = 'abc123'
        vidly_submission = VidlySubmission.objects.create(
            event=event,
            url=file_url,
            tag=tag,
        )

        event.template = self._create_default_archive_template()
        event.template_environment = {'tag': tag}
        event.save()

        url = reverse('new:vidly_media_webhook')

        xml_string = SAMPLE_MEDIA_RESULT_SUCCESS
        xml_string = re.sub(
            '<SourceFile>(.*)</SourceFile>',
            '<SourceFile>{0}</SourceFile>'.format(file_url),
            xml_string
        )
        xml_string = re.sub(
            '<MediaShortLink>(.*)</MediaShortLink>',
            '<MediaShortLink>{0}</MediaShortLink>'.format(tag),
            xml_string
        )
        response = self.client.post(url, {'xml': xml_string})
        eq_(response.status_code, 200)
        eq_('OK\n', response.content)

        event = Event.objects.get(id=event.id)
        ok_(event.archive_time)

        ok_(Picture.objects.filter(event=event))

        eq_(len(ffmpeged_urls), 1 + settings.SCREENCAPTURES_NO_PICTURES)

        vidly_submission = VidlySubmission.objects.get(id=vidly_submission.id)
        ok_(vidly_submission.finished)

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_trigger_vidly_media_webhook_private(self, p_urllib2):

        vidly_actions = []

        def make_mock_request(url, querystring):
            xml_qs = urllib.unquote(querystring)
            vidly_actions.append(
                re.findall('<Action>(.*)</Action>', xml_qs)[0]
            )
            return mock.MagicMock()

        def mocked_urlopen(request):
            xml_string = get_custom_XML(
                tag='abc123',
                status='Finished',
                private='false'
            )
            return StringIO(xml_string)

        p_urllib2.Request.side_effect = make_mock_request
        p_urllib2.urlopen = mocked_urlopen

        # the webhook is supposed to be sent back when the file has
        # been submitted and successfully transcoded.

        file_url = 'https://s3.com/foo.webm'
        event = self._create_event(file_url)

        tag = 'abc123'
        vidly_submission = VidlySubmission.objects.create(
            event=event,
            url=file_url,
            tag=tag,
            token_protection=False
        )

        event.template = self._create_default_archive_template()
        event.template_environment = {'tag': tag}
        event.privacy = Event.PRIVACY_COMPANY
        event.duration = 123
        with open(self.sample_jpg) as fp:
            picture = Picture.objects.create(
                event=event,
                file=File(fp)
            )
        event.picture = picture
        event.save()

        url = reverse('new:vidly_media_webhook')

        xml_string = SAMPLE_MEDIA_RESULT_SUCCESS
        xml_string = re.sub(
            '<SourceFile>(.*)</SourceFile>',
            '<SourceFile>{0}</SourceFile>'.format(file_url),
            xml_string
        )
        xml_string = re.sub(
            '<MediaShortLink>(.*)</MediaShortLink>',
            '<MediaShortLink>{0}</MediaShortLink>'.format(tag),
            xml_string
        )
        response = self.client.post(url, {'xml': xml_string})
        eq_(response.status_code, 200)
        eq_('OK\n', response.content)

        event = Event.objects.get(id=event.id)
        ok_(event.archive_time)

        eq_(vidly_actions, ['UpdateMedia'])

        vidly_submission = VidlySubmission.objects.get(id=vidly_submission.id)
        ok_(vidly_submission.finished)
        ok_(vidly_submission.token_protection)

    @mock.patch('requests.head')
    @mock.patch('subprocess.Popen')
    def test_trigger_vidly_media_webhook_pending(self, mock_popen, rhead):

        ffmpeged_urls = []

        def mocked_popen(command, **kwargs):
            url = destination = None
            if command[1] == '-i':
                # doing a fetch info
                url = command[2]
            elif command[1] == '-ss':
                # screen capturing
                destination = command[-1]
                assert os.path.isdir(os.path.dirname(destination))
            else:
                raise NotImplementedError(command)

            ffmpeged_urls.append(url)

            sample_jpg = self.sample_jpg

            class Inner:
                def communicate(self):
                    out = err = ''
                    if url is not None:
                        if 'abc123' in url:
                            err = """
                Duration: 00:19:17.47, start: 0.000000, bitrate: 1076 kb/s
                            """
                        else:
                            raise NotImplementedError(url)
                    elif destination is not None:
                        shutil.copyfile(sample_jpg, destination)
                    else:
                        raise NotImplementedError()
                    return out, err

            return Inner()

        mock_popen.side_effect = mocked_popen

        def mocked_head(url, **options):
            return Response(
                '',
                200
            )

        rhead.side_effect = mocked_head

        # the webhook is supposed to be sent back when the file has
        # been submitted and successfully transcoded.

        file_url = 'https://s3.com/foo.webm'
        event = self._create_event(file_url)

        tag = 'abc123'
        VidlySubmission.objects.create(
            event=event,
            url=file_url,
            tag=tag,
        )

        event.template = self._create_default_archive_template()
        event.template_environment = {'tag': tag}
        event.status = Event.STATUS_PENDING
        event.save()

        url = reverse('new:vidly_media_webhook')

        xml_string = SAMPLE_MEDIA_RESULT_SUCCESS
        xml_string = re.sub(
            '<SourceFile>(.*)</SourceFile>',
            '<SourceFile>{0}</SourceFile>'.format(file_url),
            xml_string
        )
        xml_string = re.sub(
            '<MediaShortLink>(.*)</MediaShortLink>',
            '<MediaShortLink>{0}</MediaShortLink>'.format(tag),
            xml_string
        )
        response = self.client.post(url, {'xml': xml_string})
        eq_(response.status_code, 200)
        eq_('OK\n', response.content)

        event = Event.objects.get(id=event.id)
        ok_(event.archive_time)
        eq_(event.status, Event.STATUS_SCHEDULED)

    def test_trigger_vidly_media_webhook_errored(self):

        # the webhook is supposed to be sent back when the file has
        # been submitted and successfully transcoded, or errored.

        file_url = 'https://s3.com/foo.webm'
        event = self._create_event(file_url)

        tag = 'abc123'
        vidly_submission = VidlySubmission.objects.create(
            event=event,
            url=file_url,
            tag=tag,
        )

        event.template = self._create_default_archive_template()
        event.template_environment = {'tag': tag}
        event.save()

        url = reverse('new:vidly_media_webhook')

        xml_string = SAMPLE_MEDIA_RESULT_SUCCESS
        xml_string = xml_string.replace(
            '<Status>Finished</Status>',
            '<Status>Error</Status>'
        )
        xml_string = re.sub(
            '<SourceFile>(.*)</SourceFile>',
            '<SourceFile>{0}</SourceFile>'.format(file_url),
            xml_string
        )
        xml_string = re.sub(
            '<MediaShortLink>(.*)</MediaShortLink>',
            '<MediaShortLink>{0}</MediaShortLink>'.format(tag),
            xml_string
        )
        response = self.client.post(url, {'xml': xml_string})
        eq_(response.status_code, 200)

        event = Event.objects.get(id=event.id)
        ok_(not event.archive_time)

        vidly_submission = VidlySubmission.objects.get(id=vidly_submission.id)
        ok_(vidly_submission.errored)
        ok_(not vidly_submission.finished)

    def test_trigger_vidly_media_webhook_bad_tag(self):
        self._create_event()
        url = reverse('new:vidly_media_webhook')
        xml_string = """
        <?xml version="1.0"?>
        <Response>
            <Result>
                <NoTask>This shouldn't barf too much</NoTask>
            </Result>
        </Response>
        """.strip()
        response = self.client.post(url, {'xml': xml_string})
        eq_(response.status_code, 200)

        xml_string = """
        <?xml version="1.0"?>
        <Response>
            <Result>
                <Task>
                    <MediaShortLink>xxx999</MediaShortLink>
                    <SourceFile>https://example.com</SourceFile>
                </Task>
            </Result>
        </Response>
        """.strip()

        response = self.client.post(url, {'xml': xml_string})
        eq_(response.status_code, 200)
        eq_('OK\n', response.content)

    def test_trigger_vidly_media_webhook_bad_xml(self):
        self._create_event()
        url = reverse('new:vidly_media_webhook')
        response = self.client.post(url)
        eq_(response.status_code, 400)

        response = self.client.post(url, {'xml': ''})
        eq_(response.status_code, 400)

        xml_string = SAMPLE_MEDIA_RESULT_SUCCESS
        xml_string = xml_string.replace('</', '\>')  # just screwing with it
        response = self.client.post(url, {'xml': xml_string})
        eq_(response.status_code, 400)

    @mock.patch('requests.head')
    @mock.patch('subprocess.Popen')
    def test_screencaptures(self, mock_popen, rhead):
        # this tries to make screencaptures out of the S3 upload

        ffmpeged_urls = []

        def mocked_popen(command, **kwargs):
            url = destination = None
            if command[1] == '-i':
                # doing a fetch info
                url = command[2]
            elif command[1] == '-ss':
                # screen capturing
                destination = command[-1]
                assert os.path.isdir(os.path.dirname(destination))
            else:
                raise NotImplementedError(command)

            ffmpeged_urls.append(url)

            sample_jpg = self.sample_jpg

            class Inner:
                def communicate(self):
                    out = err = ''
                    if url is not None:
                        if url == 'https://s3.com/foo.webm':
                            err = """
                Duration: 00:19:17.47, start: 0.000000, bitrate: 1076 kb/s
                            """
                        else:
                            raise NotImplementedError(url)
                    elif destination:
                        shutil.copyfile(sample_jpg, destination)
                    else:
                        raise NotImplementedError(command)
                    return out, err

            return Inner()

        mock_popen.side_effect = mocked_popen

        def mocked_head(url, **options):
            return Response(
                '',
                200
            )

        rhead.side_effect = mocked_head
        file_url = 'https://s3.com/foo.webm'
        event = self._create_event(file_url)
        assert not event.duration
        assert not Picture.objects.filter(event=event)
        assert Upload.objects.get(event=event)

        url = reverse('new:screencaptures', args=(event.id,))
        response = self.post_json(url)
        eq_(response.status_code, 200)

        event = Event.objects.get(id=event.id)
        eq_(event.duration, 1157)  # about 19m17s (see fixture)
        eq_(
            Picture.objects.filter(event=event).count(),
            settings.SCREENCAPTURES_NO_PICTURES
        )

    def test_screencaptures_default_picture(self):
        # Let's pretend we already have a couple of pictures to choose
        # from but we haven't picked one yet, then it forces the first
        # available one onto the event.
        event = self._create_event()
        event.duration = 123
        event.save()
        assert not event.picture
        assert not Picture.objects.filter(event=event)

        for _ in range(3):
            with open(self.sample_jpg) as fp:
                Picture.objects.create(
                    event=event,
                    file=File(fp)
                )

        url = reverse('new:screencaptures', args=(event.id,))
        response = self.post_json(url)
        eq_(response.status_code, 200)

        # reload and see that a picture has been chosen
        event = Event.objects.get(id=event.id)
        ok_(event.picture)

    def test_picture(self):
        event = self._create_event()
        url = reverse('new:picture', args=(event.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content)['fetching'], False)

        with open(self.sample_jpg) as fp:
            picture = Picture.objects.create(
                event=event,
                file=File(fp)
            )

        response = self.client.get(url)
        eq_(response.status_code, 200)
        thumbnails = json.loads(response.content)['thumbnails']
        thumbnail, = thumbnails
        ok_(thumbnail['url'])
        ok_(thumbnail['width'])
        ok_(thumbnail['height'])
        eq_(thumbnail['id'], picture.id)

    def test_pictures_rotate(self):
        event = self._create_event()
        url = reverse('new:pictures_rotate', args=(event.id,))
        response = self.client.get(url)
        eq_(response.status_code, 405)

        with open(self.sample_jpg) as fp:
            picture = Picture.objects.create(
                event=event,
                file=File(fp)
            )

        img_before = Image.open(picture.file.path)
        file_before = picture.file
        size_before = img_before.size
        img_before.close()

        response = self.client.post(url, {'direction': 'right'})
        eq_(response.status_code, 400)
        response = self.post_json(url, {'direction': 'right'})
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), True)
        picture = Picture.objects.get(id=picture.id)
        file_after = picture.file

        ok_(file_before != file_after)

        img_after = Image.open(picture.file.path)
        size_after = img_after.size
        img_after.close()

        # numbers transposed?
        almost_eq_(size_before[0], size_after[1], 2)
        almost_eq_(size_before[1], size_after[0], 2)

        # rotate it back
        response = self.post_json(url, {'direction': 'left'})
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), True)

        picture = Picture.objects.get(id=picture.id)
        img_after_after = Image.open(picture.file.path)
        size_after_after = img_after_after.size
        img_after_after.close()

        # numbers transposed?
        almost_eq_(size_after[0], size_after_after[1], 2)
        almost_eq_(size_after[1], size_after_after[0], 2)

        almost_eq_(size_before[0], size_after_after[0], 2)
        almost_eq_(size_before[1], size_after_after[1], 2)

    def test_picture_save(self):
        event = self._create_event()
        url = reverse('new:picture', args=(event.id,))

        # Nothing picked
        response = self.post_json(url)
        eq_(response.status_code, 400)

        # Not found picture
        response = self.post_json(url, {'picture': 0})
        eq_(response.status_code, 400)

        # Not a choice picture
        other_event = self._create_event(
            file_url='https://s3.com/bar.mp4',
            user=event.creator
        )
        assert event.id != other_event.id
        with open(self.sample_jpg) as fp:
            picture = Picture.objects.create(
                event=other_event,
                file=File(fp)
            )
        response = self.post_json(url, {'picture': picture.id})
        eq_(response.status_code, 400)

        # Finally get it right
        with open(self.sample_jpg) as fp:
            picture = Picture.objects.create(
                event=event,
                file=File(fp)
            )
        response = self.post_json(url, {'picture': picture.id})
        eq_(response.status_code, 200)

        event = Event.objects.get(id=event.id)
        eq_(event.picture, picture)

    def test_event_summary(self):
        event = self._create_event()
        url = reverse('new:summary', args=(event.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        information = json.loads(response.content)
        eq_(information['pictures'], 0)
        eq_(information['event']['status'], Event.STATUS_INITIATED)
        eq_(information['event']['title'], '')
        eq_(information['event']['description'], '')
        eq_(information['event']['tags'], '')
        eq_(information['event']['additional_links'], '')
        eq_(information['event']['slug'], '')
        eq_(information['event']['privacy'], 'public')
        # channel = Channel.objects.get(
        #     slug=settings.MOZSHORTZ_CHANNEL_SLUG
        # )
        eq_(
            information['event']['channels'], []
        )
        eq_(information['event']['id'], event.id)
        ok_(not information['event']['approvals'])

        # let's add some pictures
        with open(self.sample_jpg) as fp:
            Picture.objects.create(
                event=event,
                file=File(fp)
            )

        # and let's add some more information
        event.tags.add(Tag.objects.create(name='peterbe'))
        channel = Channel.objects.create(
            name='Peterisms',
            slug='peterisms'
        )
        event.channels.add(channel)
        topic = Topic.objects.create(topic='Sensitive Stuff')
        event.topics.add(topic)
        event.title = 'My Title'
        event.description = 'My Description'
        event.slug = 'my-title'
        event.additional_links = 'http://example.com'
        event.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        information = json.loads(response.content)
        eq_(information['pictures'], 1)
        eq_(information['event']['status'], Event.STATUS_INITIATED)
        eq_(information['event']['title'], 'My Title')
        eq_(information['event']['description'], 'My Description')
        eq_(information['event']['tags'], 'peterbe')
        eq_(information['event']['additional_links'], 'http://example.com')
        eq_(information['event']['slug'], 'my-title')
        eq_(
            information['event']['channels'],
            [
                {
                    'url': reverse('main:home_channels', args=(channel.slug,)),
                    'name': channel.name,
                    'id': channel.id,
                }
            ]
        )
        eq_(
            information['event']['topics'],
            [
                {
                    'topic': topic.topic,
                    'id': topic.id
                }
            ]
        )

    def test_event_summary_picture(self):
        """get the event summary on an event with a chosen picture"""
        event = self._create_event()
        with open(self.sample_jpg) as fp:
            picture = Picture.objects.create(
                event=event,
                file=File(fp)
            )
        event.picture = picture
        event.save()

        url = reverse('new:summary', args=(event.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        information = json.loads(response.content)
        ok_(information['event']['picture'])

    def test_event_summary_extended(self):
        event = self._create_event()
        event.slug = 'saling'
        event.save()
        channel = Channel.objects.create(name='Peterisms', slug='peterism')
        event.channels.add(channel)
        Approval.objects.create(
            event=event,
            group=Group.objects.create(name='PR')
        )
        url = reverse('new:summary', args=(event.id,))
        response = self.client.get(url, {'extended': True})
        eq_(response.status_code, 200)
        information = json.loads(response.content)
        eq_(
            information['event']['url'],
            reverse('main:event', args=(event.slug,))
        )
        # default = Channel.objects.get(slug=settings.MOZSHORTZ_CHANNEL_SLUG)
        eq_(
            information['event']['channels'],
            [
                # {
                #     'url': reverse(
                #         'main:home_channels',
                #         args=(default.slug,)
                #     ),
                #     'name': default.name,
                #     'id': default.id,
                # },
                {
                    'url': reverse(
                        'main:home_channels',
                        args=(channel.slug,)
                    ),
                    'name': channel.name,
                    'id': channel.id,
                }
            ]
        )
        eq_(information['event']['approvals'], [{'group_name': 'PR'}])

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_event_video(self, p_urllib2):

        def mocked_urlopen(request):
            xml_string = get_custom_XML(
                tag='abc123',
                status='Finished'
            )
            return StringIO(xml_string)

        p_urllib2.urlopen = mocked_urlopen

        event = self._create_event()
        url = reverse('new:video', args=(event.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), {})

        event.duration = 60 * 60 + 30 * 60
        event.template = self._create_default_archive_template()
        event.template_environment = {'tag': 'abc123'}
        event.save()

        vidly_submission = VidlySubmission.objects.create(
            event=event,
            tag='abc123',
            url='https://example.com/file.mov'
        )

        response = self.client.get(url)
        eq_(response.status_code, 200)
        information = json.loads(response.content)
        eq_(information['duration'], event.duration)
        eq_(information['duration_human'], '1 hour 30 minutes')
        ok_(information['finished'])
        eq_(information['tag'], 'abc123')
        eq_(information['status'], 'Finished')

        vidly_submission = VidlySubmission.objects.get(id=vidly_submission.id)
        ok_(vidly_submission.finished)

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_event_video_errored(self, p_urllib2):

        def mocked_urlopen(request):
            xml_string = get_custom_XML(
                tag='abc123',
                status='Error'
            )
            return StringIO(xml_string)

        p_urllib2.urlopen = mocked_urlopen

        event = self._create_event()
        url = reverse('new:video', args=(event.id,))

        event.template = self._create_default_archive_template()
        event.template_environment = {'tag': 'abc123'}
        event.save()

        vidly_submission = VidlySubmission.objects.create(
            event=event,
            tag='abc123',
            url='https://example.com/file.mov'
        )

        response = self.client.get(url)
        eq_(response.status_code, 200)
        information = json.loads(response.content)
        ok_(not information['finished'])
        eq_(information['tag'], 'abc123')
        eq_(information['status'], 'Error')

        vidly_submission = VidlySubmission.objects.get(id=vidly_submission.id)
        ok_(not vidly_submission.finished)
        ok_(vidly_submission.errored)

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_event_video_processing_and_time_estimate(self, p_urllib2):

        def mocked_urlopen(request):
            xml_string = get_custom_XML(
                tag='abc123',
                status='Processing'
            )
            return StringIO(xml_string)

        p_urllib2.urlopen = mocked_urlopen

        event = self._create_event()
        url = reverse('new:video', args=(event.id,))

        event.template = self._create_default_archive_template()
        event.template_environment = {'tag': 'abc123'}
        event.duration = 123
        event.save()

        VidlySubmission.objects.create(
            event=event,
            tag='abc123',
            url='https://example.com/file.mov'
        )

        response = self.client.get(url)
        eq_(response.status_code, 200)
        information = json.loads(response.content)
        ok_(not information['finished'])
        eq_(information['tag'], 'abc123')
        eq_(information['status'], 'Processing')
        # not enough vidly submissions to calculate a least square slope
        eq_(information['estimated_time_left'], None)

        event2 = Event.objects.create(
            duration=305,
            start_time=event.start_time,
            slug='event2'
        )
        now = timezone.now()
        VidlySubmission.objects.create(
            event=event2,
            submission_time=now,
            finished=now + datetime.timedelta(seconds=event2.duration * 2)
        )
        event3 = Event.objects.create(
            duration=500,
            start_time=event.start_time,
            slug='event3'
        )
        VidlySubmission.objects.create(
            event=event3,
            submission_time=now,
            finished=now + datetime.timedelta(seconds=event3.duration * 2)
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        information = json.loads(response.content)
        eq_(information['estimated_time_left'], 856)

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_videos(self, p_urllib2):

        def mocked_urlopen(request):
            xml_string = get_custom_XML(
                tag='abc123',
                status='Finished'
            )
            return StringIO(xml_string)

        p_urllib2.urlopen = mocked_urlopen

        event = self._create_event()
        url = reverse('new:videos')
        response = self.client.get(url)
        eq_(response.status_code, 405)
        response = self.client.post(url)
        eq_(response.status_code, 400)
        response = self.post_json(url, {'ids': [event.id]})
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), {})

        event.duration = 60 * 60 + 30 * 60
        event.template = self._create_default_archive_template()
        event.template_environment = {'tag': 'abc123'}
        event.save()

        vidly_submission = VidlySubmission.objects.create(
            event=event,
            tag='abc123',
            url='https://example.com/file.mov'
        )

        response = self.post_json(url, {'ids': [event.id]})
        eq_(response.status_code, 200)
        information = json.loads(response.content)
        event_information = information[str(event.id)]
        eq_(event_information['duration'], event.duration)
        eq_(event_information['duration_human'], '1 hour 30 minutes')
        ok_(event_information['finished'])
        eq_(event_information['tag'], 'abc123')
        eq_(event_information['status'], 'Finished')

        vidly_submission = VidlySubmission.objects.get(id=vidly_submission.id)
        ok_(vidly_submission.finished)

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_event_publish_unfinished_video(self, p_urllib2):
        """test publishing when the vidly submission hasn't finished yet"""
        group, group_users = self._create_approval_group()

        def mocked_urlopen(request):
            xml_string = get_custom_XML(
                tag='abc123',
                status='Processing'
            )
            return StringIO(xml_string)

        p_urllib2.urlopen = mocked_urlopen

        event = self._create_event()
        event.titie = 'My Title'
        event.template = self._create_default_archive_template()
        event.template_environment = {'tag': 'abc123'}
        event.save()

        topic = Topic.objects.create(topic='Money Matters')
        topic.groups.add(group)
        event.topics.add(topic)

        VidlySubmission.objects.create(
            event=event,
            tag='abc123',
            url='https://example.com/file.mov'
        )

        with open(self.sample_jpg) as fp:
            default_picture = Picture.objects.create(
                file=File(fp),
                default_placeholder=True
            )

        url = reverse('new:publish', args=(event.id,))
        response = self.post_json(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), True)

        event = Event.objects.get(id=event.id)
        eq_(event.picture, default_picture)
        eq_(event.status, Event.STATUS_PENDING)

        sent_email = mail.outbox[-1]
        ok_('Approval requested' in sent_email.subject)
        ok_(event.title in sent_email.subject)
        ok_(event.creator.email in sent_email.body)
        ok_(group.name in sent_email.body)
        eq_(sent_email.recipients(), [x.email for x in group_users])

        ok_(Approval.objects.filter(event=event, group=group))

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_event_publish_finished_video(self, p_urllib2):
        """test publishing when the vidly submission has finished"""
        group, group_users = self._create_approval_group()

        def mocked_urlopen(request):
            xml_string = get_custom_XML(
                tag='abc123',
                status='Finished'
            )
            return StringIO(xml_string)

        p_urllib2.urlopen = mocked_urlopen

        event = self._create_event()
        event.template = self._create_default_archive_template()
        event.template_environment = {'tag': 'abc123'}
        event.privacy = Event.PRIVACY_PUBLIC
        event.save()

        channel = Channel.objects.create(name='Peterism', slug='peter')
        event.channels.add(channel)

        topic = Topic.objects.create(topic='Money Matters')
        topic.groups.add(group)
        event.topics.add(topic)

        # also, create a default one
        default_channel = Channel.objects.create(
            name='Clips', slug='clips', default=True
        )

        VidlySubmission.objects.create(
            event=event,
            tag='abc123',
            url='https://example.com/file.mov'
        )

        with open(self.sample_jpg) as fp:
            picture = Picture.objects.create(
                event=event,
                file=File(fp),
            )
        event.picture = picture
        event.save()

        url = reverse('new:publish', args=(event.id,))
        response = self.post_json(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), True)

        event = Event.objects.get(id=event.id)
        ok_(channel in event.channels.all())
        ok_(default_channel not in event.channels.all())
        eq_(event.picture, picture)
        eq_(event.status, Event.STATUS_SCHEDULED)

        sent_email = mail.outbox[-1]
        ok_('Approval requested' in sent_email.subject)
        ok_(event.title in sent_email.subject)
        ok_(event.creator.email in sent_email.body)
        ok_(group.name in sent_email.body)
        eq_(sent_email.recipients(), [x.email for x in group_users])

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_event_publish_private_event(self, p_urllib2):
        """test publishing when the vidly submission has finished"""
        group, group_users = self._create_approval_group()

        vidly_actions = []

        def mocked_urlopen(request):
            xml_string = get_custom_XML(
                tag='abc123',
                status='Finished'
            )
            return StringIO(xml_string)

        def make_mock_request(url, querystring):
            xml_qs = urllib.unquote(querystring)
            vidly_actions.append(
                re.findall('<Action>(.*)</Action>', xml_qs)[0]
            )
            return mock.MagicMock()

        p_urllib2.Request.side_effect = make_mock_request
        p_urllib2.urlopen = mocked_urlopen

        event = self._create_event()
        event.template = self._create_default_archive_template()
        event.template_environment = {'tag': 'abc123'}
        event.privacy = Event.PRIVACY_PUBLIC
        event.save()

        channel = Channel.objects.create(name='Peterism', slug='peter')
        event.channels.add(channel)

        topic = Topic.objects.create(topic='Money Matters')
        topic.groups.add(group)
        event.topics.add(topic)

        # also, create a default one
        Channel.objects.create(
            name='Clips', slug='clips', default=True
        )

        submission = VidlySubmission.objects.create(
            event=event,
            tag='abc123',
            url='https://example.com/file.mov'
        )
        assert not submission.token_protection

        with open(self.sample_jpg) as fp:
            picture = Picture.objects.create(
                event=event,
                file=File(fp),
            )
        event.picture = picture

        # let's pretend you went back to set the privacy to non-public
        event.privacy = Event.PRIVACY_COMPANY
        event.save()

        url = reverse('new:publish', args=(event.id,))
        response = self.post_json(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), True)

        submission = VidlySubmission.objects.get(id=submission.id)
        ok_(submission.token_protection)

        eq_(vidly_actions, ['GetStatus', 'UpdateMedia'])

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_event_publish_private_event_not_finished(self, p_urllib2):
        """test publishing when the vidly submission has finished"""
        group, group_users = self._create_approval_group()

        vidly_actions = []

        def mocked_urlopen(request):
            xml_string = get_custom_XML(
                tag='abc123',
                status='Processing'
            )
            return StringIO(xml_string)

        def make_mock_request(url, querystring):
            xml_qs = urllib.unquote(querystring)
            vidly_actions.append(
                re.findall('<Action>(.*)</Action>', xml_qs)[0]
            )
            return mock.MagicMock()

        p_urllib2.Request.side_effect = make_mock_request
        p_urllib2.urlopen = mocked_urlopen

        event = self._create_event()
        event.template = self._create_default_archive_template()
        event.template_environment = {'tag': 'abc123'}
        event.privacy = Event.PRIVACY_PUBLIC
        event.save()

        channel = Channel.objects.create(name='Peterism', slug='peter')
        event.channels.add(channel)

        topic = Topic.objects.create(topic='Money Matters')
        topic.groups.add(group)
        event.topics.add(topic)

        # also, create a default one
        Channel.objects.create(
            name='Clips', slug='clips', default=True
        )

        submission = VidlySubmission.objects.create(
            event=event,
            tag='abc123',
            url='https://example.com/file.mov'
        )
        assert not submission.token_protection

        with open(self.sample_jpg) as fp:
            picture = Picture.objects.create(
                event=event,
                file=File(fp),
            )
        event.picture = picture

        # let's pretend you went back to set the privacy to non-public
        event.privacy = Event.PRIVACY_COMPANY
        event.save()

        url = reverse('new:publish', args=(event.id,))
        response = self.post_json(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), True)

        submission = VidlySubmission.objects.get(id=submission.id)
        ok_(submission.token_protection)

        eq_(vidly_actions, ['GetStatus'])

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_event_publish_default_channel(self, p_urllib2):
        """test publishing when the vidly submission has finished"""
        group, group_users = self._create_approval_group()

        def mocked_urlopen(request):
            xml_string = get_custom_XML(
                tag='abc123',
                status='Finished'
            )
            return StringIO(xml_string)

        p_urllib2.urlopen = mocked_urlopen

        event = self._create_event()
        event.template = self._create_default_archive_template()
        event.template_environment = {'tag': 'abc123'}
        event.privacy = Event.PRIVACY_COMPANY
        event.save()

        VidlySubmission.objects.create(
            event=event,
            tag='abc123',
            url='https://example.com/file.mov'
        )

        with open(self.sample_jpg) as fp:
            picture = Picture.objects.create(
                event=event,
                file=File(fp),
            )
        event.picture = picture
        event.save()

        assert not event.channels.all()

        channel = Channel.objects.create(
            name='Peterism',
            slug='peter',
            default=True
        )

        url = reverse('new:publish', args=(event.id,))
        response = self.post_json(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), True)

        event = Event.objects.get(id=event.id)
        ok_(channel in event.channels.all())

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_event_publish_youtube_video(self, p_urllib2):
        """test publishing when the vidly submission has finished"""
        # group, group_users = self._create_approval_group()

        event = self._create_event()
        event.template = self._create_youtube_template()
        event.template_environment = {'id': 'abc123'}
        event.privacy = Event.PRIVACY_PUBLIC
        event.save()

        with open(self.sample_jpg) as fp:
            picture = Picture.objects.create(
                event=event,
                file=File(fp),
            )
        event.picture = picture
        event.save()

        assert not event.channels.all()

        channel = Channel.objects.create(
            name='Peterism',
            slug='peter',
            default=True
        )

        url = reverse('new:publish', args=(event.id,))
        response = self.post_json(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), True)

        event = Event.objects.get(id=event.id)
        eq_(event.status, Event.STATUS_SCHEDULED)
        ok_(channel in event.channels.all())

    def test_event_publish_bad_status(self):
        event = self._create_event()
        event.status = Event.STATUS_PENDING
        event.save()
        url = reverse('new:publish', args=(event.id,))
        response = self.post_json(url)
        eq_(response.status_code, 400)

    @mock.patch('airmozilla.manage.vidly.urllib2')
    def test_publish_with_default_channel(self, p_urllib2):

        def mocked_urlopen(request):
            xml_string = get_custom_XML(
                tag='abc123',
                status='Processing'
            )
            return StringIO(xml_string)

        p_urllib2.urlopen = mocked_urlopen

        event = self._create_event()
        event.template = self._create_default_archive_template()
        event.template_environment = {'tag': 'abc123'}
        event.save()
        VidlySubmission.objects.create(
            event=event,
            tag='abc123',
            url='https://example.com/file.mov'
        )

        # suppose you unselect any channel
        url = reverse('new:edit', args=(event.id,))
        data = {
            'title': 'Some Title',
            'description': 'Some description',
            'privacy': Event.PRIVACY_COMPANY,
            'channels': [],
        }
        response = self.post_json(url, data)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content)['event']['channels'], {})
        eq_(json.loads(response.content)['event']['topics'], {})
        assert not event.channels.all().count()

        url = reverse('new:publish', args=(event.id,))
        response = self.client.post(url)
        eq_(response.status_code, 200)

    def test_your_events(self):
        event = self._create_event()
        upload = event.upload
        url = reverse('new:your_events')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        events = json.loads(response.content)['events']
        first, = events
        eq_(first['id'], event.id)
        eq_(first['title'], '')
        eq_(first['picture'], None)
        eq_(first['pictures'], 0)
        eq_(first['upload'], {
            'mime_type': upload.mime_type,
            'size': upload.size
        })

        # make some pictures available and pick one
        for i in range(3):
            with open(self.sample_jpg) as fp:
                picture = Picture.objects.create(
                    event=event,
                    file=File(fp),
                    notes=str(i)
                )
        event.picture = picture
        event.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        events = json.loads(response.content)['events']
        first, = events
        eq_(first['pictures'], 3)
        ok_(first['picture']['url'])
        ok_(first['picture']['width'])
        ok_(first['picture']['height'])

    def test_your_events_youtube_event(self):
        event = self._create_youtube_event()
        url = reverse('new:your_events')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        events = json.loads(response.content)['events']
        event, = events
        ok_(event['picture'])
        ok_(not event['upload'])

    def test_delete_event(self):
        event = self._create_event()
        url = reverse('new:delete', args=(event.id,))
        response = self.client.post(url)
        eq_(response.status_code, 200)
        eq_(json.loads(response.content), True)
        ok_(Event.objects.get(id=event.id, status=Event.STATUS_REMOVED))

    def test_picking_up_lingering_uploads(self):
        user = self._login()
        upload = Upload.objects.create(
            user=user,
            url='https://aws.com/file.mov',
            size=1234,
            mime_type='video/quicktime',
        )
        Upload.objects.create(
            user=user,
            url='https://aws.com/file2.mov',
            size=0,
            mime_type='video/quicktime',
        )
        Upload.objects.create(
            user=user,
            url='https://aws.com/file2.xls',
            size=1000,
            mime_type='application/ms-excel',
        )
        url = reverse('new:your_events')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        events = json.loads(response.content)['events']
        first, = events
        eq_(first['title'], '')
        eq_(first['upload']['size'], upload.size)
        eq_(first['upload']['mime_type'], 'video/quicktime')
        # reload
        upload = Upload.objects.get(id=upload.id)
        ok_(upload.event)
        eq_(upload.event.upload, upload)

    @mock.patch('airmozilla.base.youtube.build')
    def test_youtube_extract(self, build):

        def mocked_videos_list(id=None, **kwargs):

            def inner_list():
                if id == '0x0x0x0x0x0':
                    return {
                        'items': []
                    }
                if id == '1a1a1a1a1a1':
                    thumbnails = {
                        'high': {
                            'width': 1028,
                            'height': 720,
                            'url': 'https://youtubecdn.c0m/big.jpg'
                        }
                    }
                    return {
                        'items': [
                            {
                                'id': '1a1a1a1a1a1',
                                'snippet': {
                                    'title': 'Some Title',
                                    'description': 'Some Description',
                                    'thumbnails': thumbnails,
                                    'tags': ['Tag 1', 'Tag 2'],
                                    'channelId': 'ccchhhaaannnnnneeelll',
                                },
                                'contentDetails': {
                                    'duration': 'PT1M45S',
                                },

                            }
                        ]
                    }
                raise NotImplementedError(id)

            result = inner_list()
            obj = mock.MagicMock()
            obj.execute.return_value = result
            return obj

        def mocked_channels_list(id=None, **kwargs):

            def inner_list():
                if id == 'ccchhhaaannnnnneeelll':
                    thumbnails = {
                        'high': {
                            'width': 1028,
                            'height': 720,
                            'url': 'https://youtubecdn.c0m/big.jpg'
                        }
                    }
                    return {
                        'items': [
                            {
                                'id': 'ccchhhaaannnnnneeelll',
                                'snippet': {
                                    'title': 'Some Channel',
                                    'description': 'Channel Description',
                                    'thumbnails': thumbnails,
                                },
                            }
                        ]
                    }
                raise NotImplementedError(id)

            result = inner_list()
            obj = mock.MagicMock()
            obj.execute.return_value = result
            return obj

        def mocked_build(*args, **params):
            assert params['developerKey'] == settings.YOUTUBE_API_KEY
            api = mock.MagicMock()
            api.videos().list.side_effect = mocked_videos_list
            api.channels().list.side_effect = mocked_channels_list
            return api

        build.side_effect = mocked_build

        url = reverse('new:youtube_extract')
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 400)
        response = self.client.get(url, {'url': 'junk'})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        ok_(data['error'])

        response = self.client.get(url, {'url': 'junk'})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        ok_(data['error'])

        youtube_url = 'https://www.youtube.com/watch?v=0x0x0x0x0x0'
        response = self.client.get(url, {'url': youtube_url})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        ok_('0x0x0x0x0x0' in data['error'])

        youtube_url = 'https://www.youtube.com/watch?v=1a1a1a1a1a1'
        response = self.client.get(url, {'url': youtube_url})
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        ok_('error' not in data)
        eq_(data['title'], 'Some Title')
        eq_(data['description'], 'Some Description')
        eq_(data['thumbnail_url'], 'https://youtubecdn.c0m/big.jpg')
        eq_(data['duration'], 1 * 60 + 45)
        eq_(data['tags'], ['Tag 1', 'Tag 2'])
        eq_(data['id'], '1a1a1a1a1a1')
        eq_(data['channel']['title'], 'Some Channel')
        eq_(data['channel']['id'], 'ccchhhaaannnnnneeelll')
        eq_(data['channel']['description'], 'Channel Description')
        eq_(data['channel']['thumbnail_url'], 'https://youtubecdn.c0m/big.jpg')

    @mock.patch('requests.get')
    @mock.patch('airmozilla.base.youtube.build')
    def test_youtube_create(self, build, rget):

        def mocked_videos_list(id=None, **kwargs):

            def inner_list():
                if id == '0x0x0x0x0x0':
                    return {
                        'items': []
                    }
                if id == '1a1a1a1a1a1':
                    thumbnails = {
                        'high': {
                            'width': 1028,
                            'height': 720,
                            'url': 'https://youtubecdn.c0m/big.jpg'
                        }
                    }
                    return {
                        'items': [
                            {
                                'id': '1a1a1a1a1a1',
                                'snippet': {
                                    'title': 'Some Title',
                                    'description': 'Some Description',
                                    'thumbnails': thumbnails,
                                    'tags': ['Tag 1', 'Tag 2'],
                                    'channelId': 'ccchhhaaannnnnneeelll',
                                },
                                'contentDetails': {
                                    'duration': 'PT1M45S',
                                },

                            }
                        ]
                    }
                raise NotImplementedError(id)

            result = inner_list()
            obj = mock.MagicMock()
            obj.execute.return_value = result
            return obj

        def mocked_channels_list(id=None, **kwargs):

            def inner_list():
                if id == 'ccchhhaaannnnnneeelll':
                    thumbnails = {
                        'high': {
                            'width': 1028,
                            'height': 720,
                            'url': 'https://youtubecdn.c0m/channel.jpg'
                        }
                    }
                    return {
                        'items': [
                            {
                                'id': 'ccchhhaaannnnnneeelll',
                                'snippet': {
                                    'title': 'Some Channel',
                                    'description': 'Channel Description',
                                    'thumbnails': thumbnails,
                                },
                            }
                        ]
                    }
                raise NotImplementedError(id)

            result = inner_list()
            obj = mock.MagicMock()
            obj.execute.return_value = result
            return obj

        def mocked_build(*args, **params):
            assert params['developerKey'] == settings.YOUTUBE_API_KEY
            api = mock.MagicMock()
            api.videos().list.side_effect = mocked_videos_list
            api.channels().list.side_effect = mocked_channels_list
            return api

        build.side_effect = mocked_build

        def mocked_get(url):
            if url.endswith('big.jpg') or url.endswith('channel.jpg'):
                with open(self.sample_jpg, 'rb') as f:
                    return Response(f.read())
            raise NotImplementedError(url)

        rget.side_effect = mocked_get

        url = reverse('new:youtube_create')
        response = self.client.get(url)
        eq_(response.status_code, 405)
        response = self.client.post(url)
        eq_(response.status_code, 302)
        self._login()
        response = self.client.post(url)
        eq_(response.status_code, 400)
        response = self.post_json(url, {'other': 'stuff'})
        eq_(response.status_code, 400)
        response = self.post_json(url, {'id': '1a1a1a1a1a1'})
        eq_(response.status_code, 200)
        event_data = json.loads(response.content)
        eq_(event_data['youtube_id'], '1a1a1a1a1a1')

        event = Event.objects.get(id=event_data['id'])
        eq_(event.status, Event.STATUS_INITIATED)
        ok_(Tag.objects.get(name='Tag 1') in event.tags.all())
        ok_(Tag.objects.get(name='Tag 2') in event.tags.all())
        eq_(event.title, 'Some Title')
        eq_(event.description, 'Some Description')

        channel = Channel.objects.get(name='Some Channel')
        ok_(channel in event.channels.all())
        # this channel will be created in a parent channel called YouTube
        eq_(channel.parent.name, u'YouTube\u2122')
        eq_(channel.parent.slug, 'youtube')
