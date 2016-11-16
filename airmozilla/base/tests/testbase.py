import os
import shutil
import json
import logging

import mock
import simplejson
from nose.plugins.skip import SkipTest
from selenium import webdriver

from django.test import TestCase, LiveServerTestCase
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files import File
from django.utils import timezone

from pipeline.storage import PipelineCachedStorage
from sorl.thumbnail.kvstores.base import KVStoreBase
from sorl.thumbnail.engines.base import EngineBase

# Calm down the overly verbose sorl.thumbnail logging
logging.getLogger('sorl.thumbnail.base').setLevel(logging.INFO)


class DjangoTestCase(TestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']
    main_image = 'airmozilla/manage/tests/firefox.png'

    def setUp(self):
        super(DjangoTestCase, self).setUp()
        self._upload_media(self.main_image)
        self.created_static_files = []

        self.fanout_patcher = mock.patch('airmozilla.base.utils.fanout')
        self.fanout = self.fanout_patcher.start()

        # Every request goes through a piece of middleware that checks
        # that users with ID tokens still have valid ID tokens.
        # Not only does this add overhead, it also means any patching
        # of `requests.post` would get confused with this.
        # So we mock the whole function.
        # If a particular unit test wants to really test this function
        # they can set `self.auth0_renew.side_effect = their_own_mock_func`
        self.auth0_renew_patcher = mock.patch(
            'airmozilla.authentication.auth0.renew_id_token'
        )
        self.auth0_renew = self.auth0_renew_patcher.start()
        self.auth0_renew.side_effect = lambda x: x

    def tearDown(self):
        assert os.path.basename(settings.MEDIA_ROOT).startswith('test')
        if os.path.isdir(settings.MEDIA_ROOT):
            shutil.rmtree(settings.MEDIA_ROOT)
        for file_path in self.created_static_files:
            os.remove(file_path)
        self.fanout_patcher.stop()
        self.auth0_renew_patcher.stop()
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
    def __init__(
        self,
        content=None,
        status_code=200,
        headers=None,
        require_valid_json=False,
    ):
        self.content = content
        self.text = content
        self.status_code = status_code
        self.headers = headers or {}
        self.require_valid_json = require_valid_json

    def json(self):
        if self.require_valid_json and isinstance(self.content, basestring):
            simplejson.loads(self.content)
        return self.content

    def iter_content(self, chunk_size=1024):
        increment = 0
        while True:
            chunk = self.content[increment: increment + chunk_size]
            increment += chunk_size
            if not chunk:
                break
            yield chunk


class FastSorlKVStore(KVStoreBase):

    def __init__(self):
        self.cache = {}

    def clear(self, delete_thumbnails=False):
        self.cache = {}
        if delete_thumbnails:
            # XXX does this ever happen in tests?
            self.delete_all_thumbnail_files()

    def _get_raw(self, key):
        return self.cache.get(key)

    def _set_raw(self, key, value):
        self.cache[key] = value

    def _delete_raw(self, *keys):
        for key in keys:
            del self.cache[key]

    def _find_keys_raw(self, prefix):
        return [x for x in self.cache.keys() if x.startswith(prefix)]


class _Image(object):
    def __init__(self):
        self.size = (1000, 1000)
        self.mode = 'RGBA'
        self.data = '\xa0'


class FastSorlEngine(EngineBase):

    def get_image(self, source):
        return _Image()

    def get_image_size(self, image):
        return image.size

    def _colorspace(self, image, colorspace):
        return image

    def _scale(self, image, width, height):
        image.size = (width, height)
        return image

    def _crop(self, image, width, height, x_offset, y_offset):
        image.size = (width, height)
        return image

    def _get_raw_data(self, image, *args, **kwargs):
        return image.data

    def is_valid_image(self, raw_data):
        return bool(raw_data)
