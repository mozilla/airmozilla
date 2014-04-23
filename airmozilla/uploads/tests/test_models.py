from django.contrib.auth.models import User
from django.test import TestCase

from airmozilla.uploads.models import Upload


class UploadTestCase(TestCase):

    def test_create_upload_instance(self):
        bob = User.objects.create(username='bob')
        massive_size = 3 * 1024 * 1024 * 1024  # 3Gb
        # basically, this should be possible to create
        Upload.objects.create(
            user=bob,
            url='http://aws.com/foo.mpg',
            file_name='foo.mpg',
            mime_type='video/mpeg',
            size=massive_size
        )
