from nose.tools import ok_

from django.core.files import File
from django.core.urlresolvers import reverse

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.manage import widgets
from airmozilla.main.models import (
    Event,
    Picture
)


class TestWidgets(DjangoTestCase):

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

        # do it with it not being editable
        instance = widgets.PictureWidget(event, editable=False)
        html = instance.render('picture', picture.id)
        ok_('href="%s"' % reverse('manage:picturegallery') not in html)
