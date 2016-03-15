import os
import shutil
import json
import logging

from nose.plugins.skip import SkipTest
from selenium import webdriver

from django.test import TestCase, LiveServerTestCase
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files import File
from django.utils import timezone

from pipeline.storage import PipelineCachedStorage

# Calm down the overly verbose sorl.thumbnail logging
logging.getLogger('sorl.thumbnail.base').setLevel(logging.INFO)


class DjangoTestCase(TestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']
    main_image = 'airmozilla/manage/tests/firefox.png'

    def setUp(self):
        super(DjangoTestCase, self).setUp()
        self._upload_media(self.main_image)
        self.created_static_files = []

    def tearDown(self):
        assert os.path.basename(settings.MEDIA_ROOT).startswith('test')
        if os.path.isdir(settings.MEDIA_ROOT):
            shutil.rmtree(settings.MEDIA_ROOT)
        for file_path in self.created_static_files:
            os.remove(file_path)
        super(DjangoTestCase, self).tearDown()

    def _create_static_file(self, name, content):
        file_path = os.path.join(settings.STATIC_ROOT, name)
        with open(file_path, 'wb') as f:
            self.created_static_files.append(file_path)
            f.write(content)
        storage = PipelineCachedStorage()
        return storage.url(name)

    def shortDescription(self):
        # Stop nose using the test docstring and instead the test method name.
        pass

    def post_json(self, path, data=None, **extra):
        data = data or {}
        extra['content_type'] = 'application/json'
        return self.client.post(path, json.dumps(data), **extra)

    def _login(self, username='mary', email='mary@mozilla.com', pwd='secret'):
        user = User.objects.create_user(
            username,
            email,
            pwd,
            last_login=timezone.now()
        )
        assert self.client.login(username=username, password=pwd)
        return user

    def _attach_file(self, event, image):
        with open(image, 'rb') as f:
            img = File(f)
            event.placeholder_img.save(os.path.basename(image), img)
            assert os.path.isfile(event.placeholder_img.path)

    def _upload_media(self, image_path):
        # make sure the main_image is actually accessible
        if not os.path.isdir(settings.MEDIA_ROOT):
            os.mkdir(settings.MEDIA_ROOT)
        shutil.copy(
            image_path,
            settings.MEDIA_ROOT
        )


class DjangoLiveServerTestCase(LiveServerTestCase):

    @classmethod
    def setUpClass(cls):
        if settings.RUN_SELENIUM_TESTS:
            cls.driver = webdriver.Firefox()
            cls.driver.implicitly_wait(30)
            cls.base_url = cls.live_server_url
            cls.driver.set_window_size(1120, 550)
        super(DjangoLiveServerTestCase, cls).setUpClass()

    @classmethod
    def tearDownClass(cls):
        if settings.RUN_SELENIUM_TESTS:
            cls.driver.quit()
        super(DjangoLiveServerTestCase, cls).tearDownClass()

    def setUp(self):
        if not settings.RUN_SELENIUM_TESTS:
            raise SkipTest("settings.RUN_SELENIUM_TESTS is set to False")
        super(DjangoLiveServerTestCase, self).setUp()


class Response(object):
    def __init__(self, content=None, status_code=200, headers=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self.content

    def iter_content(self, chunk_size=1024):
        increment = 0
        while True:
            chunk = self.content[increment: increment + chunk_size]
            increment += chunk_size
            if not chunk:
                break
            yield chunk
