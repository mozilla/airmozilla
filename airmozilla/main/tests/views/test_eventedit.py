import json

import os
from django.contrib.auth.models import Group, User, Permission
from django.conf import settings
from django.core.files import File
from django.core.urlresolvers import reverse
from nose.tools import eq_, ok_
from airmozilla.main.models import (
    Event,
    Tag,
    Channel,
    EventRevision,
    RecruitmentMessage,
    Picture,
)
from airmozilla.base.tests.testbase import DjangoTestCase


class TestEventEdit(DjangoTestCase):
    other_image = 'airmozilla/manage/tests/other_logo.png'
    third_image = 'airmozilla/manage/tests/other_logo_reversed.png'

    def _event_to_dict(self, event):
        from airmozilla.main.views.edit import EventEditView
        return EventEditView.event_to_dict(event)

    def test_link_to_edit(self):
        event = Event.objects.get(title='Test event')
        response = self.client.get(reverse('main:event', args=(event.slug,)))
        eq_(response.status_code, 200)

        url = reverse('main:event_edit', args=(event.slug,))
        ok_(url not in response.content)
        self._login()
        response = self.client.get(reverse('main:event', args=(event.slug,)))
        eq_(response.status_code, 200)
        response_content = response.content.decode('utf-8')
        ok_(url in response_content)

    def test_cant_view(self):
        event = Event.objects.get(title='Test event')
        url = reverse('main:event_edit', args=(event.slug,))
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=(event.slug,))
        )
        response = self.client.post(url, {})
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=(event.slug,))
        )

    def test_edit_title(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        url = reverse('main:event_edit', args=(event.slug,))

        response = self.client.get(url)
        eq_(response.status_code, 302)

        user = self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)

        data = self._event_to_dict(event)
        previous = json.dumps(data)

        data = {
            'event_id': event.id,
            'previous': previous,
            'title': 'Different title',
            'short_description': event.short_description,
            'description': event.description,
            'additional_links': event.additional_links,
            'tags': ', '.join(x.name for x in event.tags.all()),
            'channels': [x.pk for x in event.channels.all()]
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=(event.slug,))
        )
        # this should have created 2 EventRevision objects.
        initial, current = EventRevision.objects.all().order_by('created')
        eq_(initial.event, event)
        eq_(current.event, event)
        eq_(initial.user, None)
        eq_(current.user, user)

        eq_(initial.title, 'Test event')
        eq_(current.title, 'Different title')
        # reload the event
        event = Event.objects.get(pk=event.pk)
        eq_(event.title, 'Different title')

    def test_edit_title_cancel(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        url = reverse('main:event_edit', args=(event.slug,))
        self._login()
        data = self._event_to_dict(event)
        previous = json.dumps(data)
        data = {
            'event_id': event.id,
            'previous': previous,
            'title': 'Different title',
            'short_description': event.short_description,
            'description': event.description,
            'additional_links': event.additional_links,
            'tags': ', '.join(x.name for x in event.tags.all()),
            'channels': [x.pk for x in event.channels.all()],
            'cancel': 'cancel',  # important!
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=(event.slug,))
        )
        ok_(not EventRevision.objects.all())
        # make sure it didn't actually change
        event = Event.objects.get(id=event.id)
        eq_(event.title, 'Test event')

    def test_edit_channel(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        main_channel = Channel.objects.get(
            slug=settings.DEFAULT_CHANNEL_SLUG
        )
        assert main_channel in event.channels.all()
        url = reverse('main:event_edit', args=(event.slug,))
        old_channel = Channel.objects.create(
            name='Old', slug='old', never_show=True
        )
        bad_channel = Channel.objects.create(
            name='Bad', slug='bad', never_show=True
        )
        good_channel = Channel.objects.create(
            name='Good', slug='good',
        )
        event.channels.add(old_channel)

        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # the Good channel should be a choice
        html = '<option value="{0}">{1}</option>'.format(
            good_channel.id, good_channel.name
        )
        ok_(html in response.content)
        # the Main channel should be in there and already selected
        html = '<option value="{0}" selected="selected">{1}</option>'.format(
            main_channel.id, main_channel.name
        )
        ok_(html in response.content)
        # the Old channel should be in there and already selected
        html = '<option value="{0}" selected="selected">{1}</option>'.format(
            old_channel.id, old_channel.name
        )
        ok_(html in response.content)
        # the bad channel shouldn't even be a choice
        html = '<option value="{0}">{1}</option>'.format(
            bad_channel.id, bad_channel.name
        )
        ok_(html not in response.content)

    def test_edit_nothing(self):
        """basically pressing save without changing anything"""
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        url = reverse('main:event_edit', args=(event.slug,))

        data = self._event_to_dict(event)
        previous = json.dumps(data)

        data = {
            'event_id': event.id,
            'previous': previous,
            'title': event.title,
            'short_description': event.short_description,
            'description': event.description,
            'additional_links': event.additional_links,
            'tags': [x.pk for x in event.tags.all()],
            'channels': [x.pk for x in event.channels.all()]
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=(event.slug,))
        )
        self._login()
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        ok_(not EventRevision.objects.all())

    def test_edit_no_image(self):
        """basically pressing save without changing anything"""
        event = Event.objects.get(title='Test event')
        event.placeholder_img = None
        event.save()
        url = reverse('main:event_edit', args=(event.slug,))

        data = self._event_to_dict(event)
        previous = json.dumps(data)

        data = {
            'event_id': event.id,
            'previous': previous,
            'title': event.title,
            'short_description': event.short_description,
            'description': event.description,
            'additional_links': event.additional_links,
            'tags': ', '.join(x.name for x in event.tags.all()),
            'channels': [x.pk for x in event.channels.all()]
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=(event.slug,))
        )
        self._login()
        response = self.client.post(url, data)
        eq_(response.status_code, 200)
        ok_('Events needs to have a picture' in
            response.context['form'].errors['__all__'])
        ok_('Events needs to have a picture' in response.content)

    def test_bad_edit_title(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        url = reverse('main:event_edit', args=(event.slug,))
        self._login()

        data = self._event_to_dict(event)
        previous = json.dumps(data)

        data = {
            'event_id': event.id,
            'previous': previous,
            'title': '',
            'short_description': event.short_description,
            'description': event.description,
            'additional_links': event.additional_links,
            'tags': ', '.join(x.name for x in event.tags.all()),
            'channels': [x.pk for x in event.channels.all()]
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 200)
        ok_('This field is required' in response.content)

    def test_edit_on_bad_url(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        url = reverse('main:event_edit', args=('xxx',))

        response = self.client.get(url)
        eq_(response.status_code, 404)

        old_slug = event.slug
        event.slug = 'new-slug'
        event.save()

        data = self._event_to_dict(event)
        previous = json.dumps(data)
        data = {
            'previous': previous,
            'title': event.title,
            'short_description': event.short_description,
            'description': event.description,
            'additional_links': event.additional_links,
            'tags': ', '.join(x.name for x in event.tags.all()),
            'channels': [x.pk for x in event.channels.all()]
        }

        url = reverse('main:event_edit', args=(old_slug,))
        response = self.client.get(url)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=(event.slug,))
        )
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=(event.slug,))
        )

        url = reverse('main:event_edit', args=(event.slug,))
        response = self.client.get(url)
        # because you're not allowed to view it
        eq_(response.status_code, 302)

        url = reverse('main:event_edit', args=(event.slug,))
        response = self.client.post(url, data)
        # because you're not allowed to view it, still
        eq_(response.status_code, 302)

    def test_edit_all_simple_fields(self):
        """similar to test_edit_title() but changing all fields
        other than the placeholder_img
        """
        event = Event.objects.get(title='Test event')
        event.tags.add(Tag.objects.create(name='testing'))
        self._attach_file(event, self.main_image)
        assert event.tags.all()
        assert event.channels.all()
        url = reverse('main:event_edit', args=(event.slug,))
        self._login()

        data = self._event_to_dict(event)
        previous = json.dumps(data)

        new_channel = Channel.objects.create(
            name='New Stuff',
            slug='new-stuff'
        )
        new_channel2 = Channel.objects.create(
            name='New Stuff II',
            slug='new-stuff-2'
        )
        data = {
            'event_id': event.id,
            'previous': previous,
            'title': 'Different title',
            'short_description': 'new short description',
            'description': 'new description',
            'additional_links': 'new additional_links',
            'tags': 'newtag',
            'channels': [new_channel.pk, new_channel2.pk]
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=(event.slug,))
        )
        # this should have created 2 EventRevision objects.
        initial, current = EventRevision.objects.all().order_by('created')
        eq_(initial.event, event)
        eq_(initial.title, 'Test event')
        eq_(current.title, 'Different title')
        # reload the event
        event = Event.objects.get(pk=event.pk)
        eq_(event.title, 'Different title')
        eq_(event.description, 'new description')
        eq_(event.short_description, 'new short description')
        eq_(event.additional_links, 'new additional_links')
        eq_(
            sorted(x.name for x in event.tags.all()),
            ['newtag']
        )
        eq_(
            sorted(x.name for x in event.channels.all()),
            ['New Stuff', 'New Stuff II']
        )

    def test_edit_recruitmentmessage(self):
        """Change the revision message from nothing, to something
        to another one.
        """
        event = Event.objects.get(title='Test event')
        event.tags.add(Tag.objects.create(name='testing'))
        self._attach_file(event, self.main_image)
        assert event.tags.all()
        assert event.channels.all()
        url = reverse('main:event_edit', args=(event.slug,))
        user = self._login()

        data = self._event_to_dict(event)
        previous = json.dumps(data)

        msg1 = RecruitmentMessage.objects.create(
            text='Web Developer',
            url='http://careers.mozilla.com/123',
            active=True
        )
        msg2 = RecruitmentMessage.objects.create(
            text='C++ Developer',
            url='http://careers.mozilla.com/456',
            active=True
        )
        msg3 = RecruitmentMessage.objects.create(
            text='Fortran Developer',
            url='http://careers.mozilla.com/000',
            active=False  # Note!
        )

        # if you don't have the right permission, you can't see this choice
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Recruitment message' not in response.content)

        # give the user the necessary permission
        recruiters = Group.objects.create(name='Recruiters')
        permission = Permission.objects.get(
            codename='change_recruitmentmessage'
        )
        recruiters.permissions.add(permission)
        user.groups.add(recruiters)
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Recruitment message' in response.content)
        ok_(msg1.text in response.content)
        ok_(msg2.text in response.content)
        ok_(msg3.text not in response.content)  # not active

        with open('airmozilla/manage/tests/firefox.png') as fp:
            picture = Picture.objects.create(file=File(fp))

        data = {
            'event_id': event.id,
            'previous': previous,
            'recruitmentmessage': msg1.pk,
            'title': event.title,
            'picture': picture.id,
            'description': event.description,
            'short_description': event.short_description,
            'channels': [x.id for x in event.channels.all()],
            'tags': [x.name for x in event.tags.all()],
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=(event.slug,))
        )

        # this should have created 2 EventRevision objects.
        initial, current = EventRevision.objects.all().order_by('created')
        eq_(initial.event, event)
        ok_(not initial.recruitmentmessage)
        eq_(current.recruitmentmessage, msg1)

        # reload the event
        event = Event.objects.get(pk=event.pk)
        eq_(event.recruitmentmessage, msg1)

        # now change it to another message
        data = self._event_to_dict(event)
        previous = json.dumps(data)
        data['recruitmentmessage'] = msg2.pk
        data['previous'] = previous
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=(event.slug,))
        )
        # reload the event
        event = Event.objects.get(pk=event.pk)
        eq_(event.recruitmentmessage, msg2)

        initial, __, current = (
            EventRevision.objects.all().order_by('created')
        )
        eq_(current.recruitmentmessage, msg2)

        # lastly, change it to blank
        data = self._event_to_dict(event)
        previous = json.dumps(data)
        data['recruitmentmessage'] = ''
        data['previous'] = previous
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('main:event', args=(event.slug,))
        )
        # reload the event
        event = Event.objects.get(pk=event.pk)
        eq_(event.recruitmentmessage, None)

        initial, __, __, current = (
            EventRevision.objects.all().order_by('created')
        )
        eq_(current.recruitmentmessage, None)

    def test_edit_placeholder_img(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        url = reverse('main:event_edit', args=(event.slug,))
        self._login()

        old_placeholder_img_path = event.placeholder_img.path

        data = self._event_to_dict(event)
        previous = json.dumps(data)

        with open(self.other_image) as fp:
            data = {
                'event_id': event.id,
                'previous': previous,
                'title': event.title,
                'short_description': event.short_description,
                'description': event.description,
                'additional_links': event.additional_links,
                'tags': ', '.join(x.name for x in event.tags.all()),
                'channels': [x.pk for x in event.channels.all()],
                'placeholder_img': fp,
            }
            response = self.client.post(url, data)
            eq_(response.status_code, 302)
            self.assertRedirects(
                response,
                reverse('main:event', args=(event.slug,))
            )
        # this should have created 2 EventRevision objects.
        initial, current = EventRevision.objects.all().order_by('created')
        ok_(initial.placeholder_img)
        ok_(current.placeholder_img)
        # reload the event
        event = Event.objects.get(pk=event.pk)
        new_placeholder_img_path = event.placeholder_img.path
        ok_(old_placeholder_img_path != new_placeholder_img_path)
        ok_(os.path.isfile(old_placeholder_img_path))
        ok_(os.path.isfile(new_placeholder_img_path))

    def test_edit_placeholder_img_to_unselect_picture(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)

        # also, let's pretend the event has a picture already selected
        with open(self.main_image) as fp:
            picture = Picture.objects.create(file=File(fp))
            event.picture = picture
            event.save()

        url = reverse('main:event_edit', args=(event.slug,))
        self._login()

        old_placeholder_img_path = event.placeholder_img.path

        data = self._event_to_dict(event)
        previous = json.dumps(data)

        with open(self.other_image) as fp:
            data = {
                'event_id': event.id,
                'previous': previous,
                'title': event.title,
                'short_description': event.short_description,
                'description': event.description,
                'additional_links': event.additional_links,
                'tags': ', '.join(x.name for x in event.tags.all()),
                'channels': [x.pk for x in event.channels.all()],
                'placeholder_img': fp,
                # this is a hidden field you can't not send
                'picture': picture.id,
            }
            response = self.client.post(url, data)
            eq_(response.status_code, 302)
            self.assertRedirects(
                response,
                reverse('main:event', args=(event.slug,))
            )

        # this should have created 2 EventRevision objects.
        initial, current = EventRevision.objects.all().order_by('created')
        ok_(initial.placeholder_img)
        ok_(current.placeholder_img)
        ok_(not current.picture)
        # reload the event
        event = Event.objects.get(pk=event.pk)
        ok_(not event.picture)
        new_placeholder_img_path = event.placeholder_img.path
        ok_(old_placeholder_img_path != new_placeholder_img_path)
        ok_(os.path.isfile(old_placeholder_img_path))
        ok_(os.path.isfile(new_placeholder_img_path))

    def test_set_new_placeholder_img_and_unselect_picture(self):
        event = Event.objects.get(title='Test event')
        event.placeholder_img = None
        event.save()

        # also, let's pretend the event has a picture already selected
        with open(self.main_image) as fp:
            picture = Picture.objects.create(file=File(fp))
            event.picture = picture
            event.save()

        url = reverse('main:event_edit', args=(event.slug,))
        self._login()

        data = self._event_to_dict(event)
        ok_(not data.get('placeholder_img'))
        previous = json.dumps(data)

        with open(self.other_image) as fp:
            data = {
                'event_id': event.id,
                'previous': previous,
                'title': event.title,
                'short_description': event.short_description,
                'description': event.description,
                'additional_links': event.additional_links,
                'tags': ', '.join(x.name for x in event.tags.all()),
                'channels': [x.pk for x in event.channels.all()],
                'placeholder_img': fp,
                # this is a hidden field you can't not send
                'picture': picture.id,
            }
            response = self.client.post(url, data)
            eq_(response.status_code, 302)
            self.assertRedirects(
                response,
                reverse('main:event', args=(event.slug,))
            )

        # this should have created 2 EventRevision objects.
        initial, current = EventRevision.objects.all().order_by('created')
        ok_(not initial.placeholder_img)
        ok_(current.placeholder_img)
        ok_(not current.picture)
        # reload the event
        event = Event.objects.get(pk=event.pk)
        ok_(not event.picture)
        new_placeholder_img_path = event.placeholder_img.path
        ok_(os.path.isfile(new_placeholder_img_path))

        initial, current = EventRevision.objects.all().order_by('created')
        ok_(current.placeholder_img)
        diff_url = reverse(
            'main:event_difference',
            args=(event.slug, initial.id,)
        )
        response = self.client.get(diff_url)
        eq_(response.status_code, 200)
        diff_url = reverse(
            'main:event_change',
            args=(event.slug, current.id,)
        )
        response = self.client.get(diff_url)
        eq_(response.status_code, 200)

    def test_edit_conflict(self):
        """You can't edit the title if someone else edited it since the
        'previous' JSON dump was taken."""
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        url = reverse('main:event_edit', args=(event.slug,))
        self._login()

        data = self._event_to_dict(event)
        previous = json.dumps(data)

        event.title = 'Sneak Edit'
        event.save()

        data = {
            'event_id': event.id,
            'previous': previous,
            'title': 'Different title',
            'short_description': event.short_description,
            'description': event.description,
            'additional_links': event.additional_links,
            'tags': ', '.join(x.name for x in event.tags.all()),
            'channels': [x.pk for x in event.channels.all()]
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 200)
        ok_('Conflict error!' in response.content)

    def test_edit_conflict_on_placeholder_img(self):
        """You can't edit the title if someone else edited it since the
        'previous' JSON dump was taken."""
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        url = reverse('main:event_edit', args=(event.slug,))
        self._login()

        data = self._event_to_dict(event)
        previous = json.dumps(data)

        self._attach_file(event, self.other_image)

        with open(self.third_image) as fp:
            data = {
                'event_id': event.id,
                'previous': previous,
                'title': event.title,
                'short_description': event.short_description,
                'description': event.description,
                'additional_links': event.additional_links,
                'tags': ', '.join(x.name for x in event.tags.all()),
                'channels': [x.pk for x in event.channels.all()],
                'placeholder_img': fp
            }
            response = self.client.post(url, data)
            eq_(response.status_code, 200)
            ok_('Conflict error!' in response.content)

    def test_edit_conflict_near_miss(self):
        """If the event changes between the time you load the edit page
        and you pressing 'Save' it shouldn't be a problem as long as
        you're changing something different."""
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)
        url = reverse('main:event_edit', args=(event.slug,))
        self._login()

        data = self._event_to_dict(event)
        previous = json.dumps(data)

        event.title = 'Sneak Edit'
        event.save()

        data = {
            'event_id': event.id,
            'previous': previous,
            'title': 'Test event',
            'short_description': 'new short description',
            'description': event.description,
            'additional_links': event.additional_links,
            'tags': ', '.join(x.name for x in event.tags.all()),
            'channels': [x.pk for x in event.channels.all()]
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)
        event = Event.objects.get(pk=event.pk)
        eq_(event.title, 'Sneak Edit')
        eq_(event.short_description, 'new short description')

    def test_view_revision_change_links(self):
        event = Event.objects.get(title='Test event')
        event.tags.add(Tag.objects.create(name='testing'))
        self._attach_file(event, self.main_image)
        url = reverse('main:event_edit', args=(event.slug,))
        user = self._login()

        data = self._event_to_dict(event)
        previous = json.dumps(data)

        data = {
            'event_id': event.id,
            'previous': previous,
            'title': 'Test event',
            'short_description': 'new short description',
            'description': event.description,
            'additional_links': event.additional_links,
            'tags': ', '.join(x.name for x in event.tags.all()),
            'channels': [x.pk for x in event.channels.all()]
        }
        response = self.client.post(url, data)
        eq_(response.status_code, 302)

        eq_(EventRevision.objects.filter(event=event).count(), 2)
        base_revision = EventRevision.objects.get(
            event=event,
            user__isnull=True
        )
        user_revision = EventRevision.objects.get(
            event=event,
            user=user
        )

        # reload the event edit page
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # because there's no difference between this and the event now
        # we should NOT have a link to see the difference for the user_revision
        response_content = response.content.decode('utf-8')
        ok_(
            reverse('main:event_difference',
                    args=(event.slug, user_revision.pk))
            not in response_content
        )
        # but there should be a link to the change
        ok_(
            reverse('main:event_change',
                    args=(event.slug, user_revision.pk))
            in response_content
        )
        # since the base revision doesn't have any changes there shouldn't
        # be a link to it
        ok_(
            reverse('main:event_change',
                    args=(event.slug, base_revision.pk))
            not in response_content
        )
        # but there should be a link to the change
        ok_(
            reverse('main:event_difference',
                    args=(event.slug, base_revision.pk))
            in response_content
        )

    def test_cant_view_all_revision_changes(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)

        # base revision
        base_revision = EventRevision.objects.create_from_event(event)

        # change the event without saving so we can make a new revision
        event.title = 'Different title'
        user = User.objects.create_user(
            'mary', 'mary@mozilla.com', 'secret'
        )
        user_revision = EventRevision.objects.create_from_event(
            event,
            user=user
        )
        change_url = reverse(
            'main:event_change',
            args=(event.slug, user_revision.pk)
        )
        difference_url = reverse(
            'main:event_difference',
            args=(event.slug, base_revision.pk)
        )
        # you're not allowed to view these if you're not signed in
        response = self.client.get(change_url)
        eq_(response.status_code, 302)

        response = self.client.get(difference_url)
        eq_(response.status_code, 302)

    def test_view_revision_change(self):
        event = Event.objects.get(title='Test event')
        event.tags.add(Tag.objects.create(name='testing'))
        self._attach_file(event, self.main_image)

        # base revision
        base_revision = EventRevision.objects.create_from_event(event)

        # change the event without saving so we can make a new revision
        event.title = 'Different title'
        event.description = 'New description'
        event.short_description = 'New short description'
        event.additional_links = 'New additional links'
        event.save()
        user = User.objects.create_user(
            'bob', 'bob@mozilla.com', 'secret'
        )
        user_revision = EventRevision.objects.create_from_event(
            event,
            user=user
        )
        user_revision.tags.add(Tag.objects.create(name='newtag'))
        user_revision.channels.remove(Channel.objects.get(name='Main'))
        user_revision.channels.add(
            Channel.objects.create(name='Web dev', slug='webdev')
        )
        with open(self.other_image, 'rb') as f:
            img = File(f)
            user_revision.placeholder_img.save(
                os.path.basename(self.other_image),
                img
            )

        # view the change
        url = reverse('main:event_change', args=(event.slug, user_revision.pk))
        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Different title' in response.content)
        ok_('New description' in response.content)
        ok_('New short description' in response.content)
        ok_('New additional links' in response.content)
        ok_('Web dev' in response.content)
        ok_('newtag, testing' in response.content)

        event.tags.add(Tag.objects.create(name='newtag'))
        event.channels.remove(Channel.objects.get(name='Main'))
        event.channels.add(
            Channel.objects.get(name='Web dev')
        )

        # view the difference
        url = reverse(
            'main:event_difference',
            args=(event.slug, base_revision.pk))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Different title' in response.content)
        ok_('New description' in response.content)
        ok_('New short description' in response.content)
        ok_('New additional links' in response.content)
        ok_('Web dev' in response.content)
        ok_('newtag, testing' in response.content)

    def test_view_revision_change_on_recruitmentmessage(self):
        event = Event.objects.get(title='Test event')
        self._attach_file(event, self.main_image)

        # base revision
        EventRevision.objects.create_from_event(event)

        user = User.objects.create_user(
            'bob', 'bob@mozilla.com', 'secret'
        )
        user_revision = EventRevision.objects.create_from_event(
            event,
            user=user
        )
        msg1 = RecruitmentMessage.objects.create(
            text='Web Developer',
            url='http://careers.mozilla.com/123',
            active=True
        )
        user_revision.recruitmentmessage = msg1
        user_revision.save()

        # view the change
        url = reverse('main:event_change', args=(event.slug, user_revision.pk))
        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_content = response.content.decode('utf-8')
        ok_(msg1.text in response_content)
