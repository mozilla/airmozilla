import os
import shutil

from django.test import TestCase
from django.conf import settings


class DjangoTestCase(TestCase):

    def shortDescription(self):
        return None

    def tearDown(self):
        assert os.path.basename(settings.MEDIA_ROOT).startswith('testmedia')
        if os.path.isdir(settings.MEDIA_ROOT):
            shutil.rmtree(settings.MEDIA_ROOT)

        super(DjangoTestCase, self).tearDown()
