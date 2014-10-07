import json

from nose.tools import eq_, ok_

from django.core.files import File

from funfactory.urlresolvers import reverse

from airmozilla.main.models import Picture
from .base import ManageTestCase


class TestPictureGallery(ManageTestCase):

    main_image = 'airmozilla/manage/tests/firefox.png'
    other_image = 'airmozilla/manage/tests/other_logo.png'

    def test_load_gallery(self):
        url = reverse('manage:picturegallery')
        response = self.client.get(url)
        eq_(response.status_code, 200)

    def test_picturegallery_data(self):
        url = reverse('manage:picturegallery_data')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response['Content-Type'], 'application/json')

        # it's no fun until you add some pictures
        with open(self.main_image) as fp:
            picture = Picture.objects.create(
                file=File(fp),
                notes="Some notes"
            )
            picture2 = Picture.objects.create(
                file=File(fp),
                notes=""
            )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        struct = json.loads(response.content)
        ok_(struct['urls'])
        p1, p2 = struct['pictures']
        # because it's sorted by 'created'
        ok_(p1['width'])
        ok_(p1['height'])
        ok_(p1['size'])
        assert p1['id'] == picture2.id
        assert p2['id'] == picture.id
        eq_(p2['notes'], 'Some notes')

        # the view is cached but it should be invalidated if you change
        # any picture
        picture.notes = 'Other notes'
        picture.save()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        struct = json.loads(response.content)
        eq_(struct['pictures'][1]['notes'], 'Other notes')

    def test_picture_edit(self):
        with open(self.main_image) as fp:
            picture = Picture.objects.create(
                file=File(fp),
                notes="Some notes"
            )

        url = reverse('manage:picture_edit', args=(picture.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Some notes' in response.content)

        with open(self.other_image) as fp:
            response = self.client.post(url, {
                'file': fp,
                'notes': 'Other notes'
            })
            eq_(response.status_code, 302)

        picture = Picture.objects.get(id=picture.id)
        eq_(picture.notes, 'Other notes')

    def test_picture_add(self):
        url = reverse('manage:picture_add')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        with open(self.other_image) as fp:
            response = self.client.post(url, {
                'file': fp
            })

        picture, = Picture.objects.all()
        assert picture.width
        assert picture.height
        assert picture.size

    def test_picture_view(self):
        with open(self.main_image) as fp:
            picture = Picture.objects.create(
                file=File(fp),
                notes="Some notes"
            )

        url = reverse('manage:picture_view', args=(picture.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)

        ok_(int(response['Content-Length']) > 0)
        eq_(response['Content-Type'], 'image/png')
        ok_(response['Cache-Control'])
        previous_content_length = int(response['Content-Length'])
        # now view it as a thumbnail
        response = self.client.get(url, {'geometry': '50x50'})
        eq_(response.status_code, 200)
        ok_(int(response['Content-Length']) < previous_content_length)
