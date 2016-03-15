import datetime
import hashlib
import json

import mock
from nose.tools import eq_, ok_

from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.uploads.models import Upload
from airmozilla.main.models import Event


class HeadResponse(object):
    def __init__(self, **headers):
        self.headers = headers


class TestUploads(DjangoTestCase):

    def test_home(self):
        url = reverse('uploads:home')
        response = self.client.get(url)
        eq_(response.status_code, 302)
        ok_(reverse('main:login') in response['location'])

        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)

    def test_upload(self):
        url = reverse('uploads:upload')
        response = self.client.get(url)
        eq_(response.status_code, 302)
        ok_(reverse('main:login') in response['location'])

        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)

    def test_sign(self):
        url = reverse('uploads:sign')
        user = self._login()

        response = self.client.get(url)
        eq_(response.status_code, 400)

        response = self.client.get(
            url,
            {'s3_object_name': 'foo.flv',
             's3_object_type': 'video/file'}
        )
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        # expect the URL to contain todays date
        s3_url = structure['url']
        now = datetime.datetime.utcnow()
        ok_(now.strftime('%Y/%m/%d') in s3_url)
        ok_(str(user.pk) in s3_url)
        ok_('.flv' in s3_url)

        signed_request = structure['signed_request']
        ok_(settings.AWS_ACCESS_KEY_ID in signed_request)
        ok_(settings.S3_UPLOAD_BUCKET in signed_request)

        # that should have set a cache key too
        cache_key = 'file_name_%s' % hashlib.md5(s3_url).hexdigest()
        eq_(cache.get(cache_key), 'foo.flv')

    def test_sign_unicode_name(self):
        url = reverse('uploads:sign')
        self._login()
        response = self.client.get(
            url,
            {'s3_object_name': u'st\xe9phanie.flv',
             's3_object_type': 'video/file'}
        )
        eq_(response.status_code, 200)

    @mock.patch('requests.head')
    def test_save(self, rhead):
        def mocked_head(url, **options):
            return HeadResponse(**{'content-length': 123456})
        rhead.side_effect = mocked_head

        url = reverse('uploads:save')
        response = self.client.post(url)
        eq_(response.status_code, 302)
        ok_(reverse('main:login') in response['location'])

        user = self._login()
        response = self.client.post(url)
        eq_(response.status_code, 400)

        response = self.client.post(url, {
            'url': 'https://aws.com/foo.flv'
        })
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        new_id = structure['id']
        upload = Upload.objects.get(pk=new_id)
        eq_(upload.size, 123456)
        eq_(upload.url, 'https://aws.com/foo.flv')
        eq_(upload.file_name, 'foo.flv')
        eq_(upload.user, user)

    @mock.patch('requests.head')
    def test_save_on_an_active_event_edit(self, rhead):
        def mocked_head(url, **options):
            return HeadResponse(**{'content-length': 123456})
        rhead.side_effect = mocked_head

        user = self._login()
        user.is_superuser = True
        user.is_staff = True
        user.save()

        event = Event.objects.get(title='Test event')
        event_upload_url = reverse('manage:event_upload', args=(event.pk,))
        response = self.client.get(event_upload_url)
        eq_(response.status_code, 200)

        url = reverse('uploads:save')
        response = self.client.post(url, {
            'url': 'https://aws.com/foo.flv'
        })
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        new_id = structure['id']
        upload = Upload.objects.get(pk=new_id)
        eq_(upload.size, 123456)
        eq_(upload.url, 'https://aws.com/foo.flv')
        eq_(upload.file_name, 'foo.flv')
        eq_(upload.user, user)
        eq_(upload.event, event)

        event = Event.objects.get(pk=event.pk)
        eq_(event.upload, upload)

    @mock.patch('requests.head')
    def test_verify_size(self, rhead):
        def mocked_head(url, **options):
            return HeadResponse(**{'content-length': 123456})
        rhead.side_effect = mocked_head
        url = reverse('uploads:verify_size')
        self._login()
        response = self.client.get(url, {'url': 'https://aws.com/foo.flv'})
        eq_(response.status_code, 200)
        structure = json.loads(response.content)
        eq_(structure['size'], 123456)
        eq_(structure['size_human'], u'120.6\xa0KB')
