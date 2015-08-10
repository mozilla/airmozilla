from nose.tools import ok_

from django.core.files import File

from airmozilla.main.models import Event, Picture
from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.base.forms import GallerySelect


class TestGallerySelect(DjangoTestCase):

    def test_render_with_name(self):
        instance = GallerySelect()
        html = instance.render('picky', None, None)
        ok_('id="id_picky"' in html)
        ok_('name="picky"' in html)

    def test_render_without_event(self):
        instance = GallerySelect()
        # add some pictures
        event = Event.objects.get(title='Test event')
        with open(self.main_image) as fp:
            pic1 = Picture.objects.create(
                file=File(fp),
                notes='Some notes'
            )
            Picture.objects.create(
                file=File(fp),
                notes='Other notes',
                event=event
            )
            Picture.objects.create(
                file=File(fp),
                notes='Inactive notes',
                is_active=False
            )

        html = instance.render('picture', None, None)
        ok_('Some notes' in html)
        ok_('data-picture-id="%s"' % pic1.id in html)
        ok_('Other notes' not in html)  # belongs to an event
        ok_('Inactive notes' not in html)  # not active

    def test_render_with_event(self):
        event = Event.objects.get(title='Test event')
        instance = GallerySelect(event=event)
        # add some pictures
        with open(self.main_image) as fp:
            Picture.objects.create(
                file=File(fp),
                notes='Some notes'
            )
            pic2 = Picture.objects.create(
                file=File(fp),
                notes='Other notes',
                event=event
            )
            Picture.objects.create(
                file=File(fp),
                notes='Inactive Notes',
                is_active=False,
            )

        html = instance.render('picture', None, None)
        ok_('Some notes' in html)
        ok_('Other notes' in html)
        ok_('Inactive notes' not in html)

        # now with a value
        html = instance.render('picture', pic2.id, None)
        # one of them should have a class "selected"
        ok_('class="selected' in html)
        ok_('Inactive notes' not in html)

    def test_render_with_event_picture_inactive(self):
        event = Event.objects.get(title='Test event')
        with open(self.main_image) as fp:
            picture = Picture.objects.create(
                file=File(fp),
                notes='Inactive notes',
                is_active=False
            )
            event.picture = picture
            event.save()

        instance = GallerySelect(event=event)

        html = instance.render('picture', None, None)
        ok_('Inactive notes' in html)
        html = instance.render('picture', picture.id, None)
        ok_('Inactive notes' in html)
