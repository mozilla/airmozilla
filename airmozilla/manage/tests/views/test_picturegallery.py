import json

from nose.tools import eq_, ok_

from django.contrib.auth.models import User, Group

from funfactory.urlresolvers import reverse

from .base import ManageTestCase


class TestPictureGallery(ManageTestCase):

    def test_load_gallery(self):
        url = reverse('manage:picturegallery')
        response = self.client.get(url)
        eq_(response.status_code, 200)

    def test_picturegallery_data(self):
        url = reverse('manage:picturegallery_data')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'application/json')
