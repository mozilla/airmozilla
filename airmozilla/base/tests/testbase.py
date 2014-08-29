import os
import shutil

from django.test import TestCase
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files import File


class DjangoTestCase(TestCase):

    def shortDescription(self):
        return None

    def tearDown(self):
        assert os.path.basename(settings.MEDIA_ROOT).startswith('testmedia')
        if os.path.isdir(settings.MEDIA_ROOT):
            shutil.rmtree(settings.MEDIA_ROOT)

        super(DjangoTestCase, self).tearDown()

    def _login(self, username='mary', email='mary@mozilla.com', pwd='secret'):
        user = User.objects.create_user(
            username, email, pwd
        )
        assert self.client.login(username=username, password=pwd)
        return user

    def _attach_file(self, event, image):
        with open(image, 'rb') as f:
            img = File(f)
            event.placeholder_img.save(os.path.basename(image), img)
            assert os.path.isfile(event.placeholder_img.path)
