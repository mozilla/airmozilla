from nose.tools import ok_

from django.test import TestCase
from django.core.files import File

from funfactory.urlresolvers import reverse

from airmozilla.manage import widgets
from airmozilla.main.models import (
    Event,
    Picture
)


class TestWidgets(TestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']
    main_image = 'airmozilla/manage/tests/firefox.png'

    def test_picture_gallery_widget(self):

        event = Event.objects.get(title='Test event')
        instance = widgets.PictureWidget(event)
        html = instance.render('picture', None)
        ok_(reverse('manage:picturegallery') in html)
        ok_('?event=%d' % event.id in html)

        with open(self.main_image) as fp:
            picture = Picture.objects.create(file=File(fp))
            event.picture = picture
            event.save()

        html = instance.render('picture', picture.id)
        ok_(reverse('manage:picture_edit', args=(picture.id,)) in html)
        ok_('type="hidden"' in html)
        ok_('value="%d"' % picture.id in html)
