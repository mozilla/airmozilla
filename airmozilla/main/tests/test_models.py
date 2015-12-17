# -*- coding: utf-8 -*-

import datetime

from django.contrib.auth.models import Group, User
from django.utils import timezone
from django.utils.timezone import utc
from django.core.files import File

from nose.tools import ok_, eq_
import mock

from airmozilla.main.models import (
    Approval,
    Event,
    EventOldSlug,
    Location,
    most_recent_event,
    RecruitmentMessage,
    Picture,
    CuratedGroup,
    VidlySubmission,
    Tag,
    VidlyMedia,
)

from airmozilla.base.tests.testbase import DjangoTestCase, Response
# This must be imported otherwise django-nose won't import
# that foreign key reference when you run only the tests in this file.
from airmozilla.uploads.models import Upload
Upload = Upload  # shut up pyflakes


class EventTests(DjangoTestCase):

    def test_location_time(self):
        date = datetime.datetime(2099, 1, 1, 18, 0, 0).replace(tzinfo=utc)
        mountain_view = Location.objects.create(
            name='Mountain View',
            timezone='US/Pacific',
        )
        event = Event.objects.create(
            status=Event.STATUS_INITIATED,
            start_time=date,
            location=mountain_view,
        )
        eq_(event.location_time.hour, 10)

        paris = Location.objects.create(
            name='Paris',
            timezone='Europe/Paris'
        )
        event.location = paris
        event.save()
        eq_(event.location_time.hour, 19)

    def test_most_recent_event(self):
        # this test does not benefit from the standard fixtures
        Event.objects.all().delete()

        date = datetime.datetime(2099, 1, 1, 18, 0, 0).replace(tzinfo=utc)
        mountain_view = Location.objects.create(
            name='Mountain View',
            timezone='US/Pacific',
        )
        eq_(most_recent_event(), None)
        event1 = Event.objects.create(
            title='Event 1',
            status=Event.STATUS_INITIATED,
            start_time=date,
            location=mountain_view,
        )
        eq_(most_recent_event(), event1)
        event2 = Event.objects.create(
            title='Event 2',
            status=Event.STATUS_INITIATED,
            start_time=date + datetime.timedelta(days=1),
            location=mountain_view,
        )
        eq_(most_recent_event(), event2)

        event1.start_time -= datetime.timedelta(days=1)
        event1.save()
        eq_(most_recent_event(), event1)

    def test_has_unique_title(self):
        event, = Event.objects.all()
        ok_(event.has_unique_title())
        # create another event
        Event.objects.create(
            title=event.title,
            slug='other',
            start_time=timezone.now(),
        )
        ok_(not event.has_unique_title())
        event.title += ' difference'
        event.save()
        ok_(event.has_unique_title())

    def test_get_unique_title(self):
        event, = Event.objects.all()
        event.title += u' Swëdish'
        event.save()
        assert event.has_unique_title()
        eq_(event.get_unique_title(), event.title)
        Event.objects.create(
            title=event.title,
            slug='other',
            start_time=timezone.now(),
        )
        assert not event.has_unique_title()
        unique_title = event.get_unique_title()
        ok_(unique_title != event.title)

        event.title += ' difference'
        event.save()
        eq_(event.get_unique_title(), event.title)


class EventStateTests(DjangoTestCase):

    def test_event_needs_approval(self):
        event = Event.objects.create(
            status=Event.STATUS_SCHEDULED,
            start_time=timezone.now(),
            archive_time=timezone.now()
        )
        ok_(not event.needs_approval())

        app = Approval.objects.create(event=event)
        ok_(event.needs_approval())

        app.processed = True
        app.save()
        ok_(not event.needs_approval())

        app.approved = True
        app.save()
        ok_(not event.needs_approval())

    def test_archived_and_approved(self):
        event = Event.objects.create(
            status=Event.STATUS_SCHEDULED,
            start_time=timezone.now(),
            archive_time=timezone.now()
        )
        ok_(event in Event.objects.archived())
        ok_(event in Event.objects.archived().approved())

        # now suppose, it as a pending approval on it
        app = Approval.objects.create(event=event)
        ok_(event in Event.objects.archived())
        ok_(event not in Event.objects.archived().approved())

        # basically, it has been looked at and the answer was no
        app.processed = True
        app.save()
        ok_(event in Event.objects.archived())
        ok_(event not in Event.objects.archived().approved())

        app.approved = True
        app.save()
        ok_(event in Event.objects.archived())
        ok_(event in Event.objects.archived().approved())

    def test_live_and_approved(self):
        event = Event.objects.create(
            status=Event.STATUS_SCHEDULED,
            start_time=timezone.now(),
        )
        ok_(event.is_live())
        ok_(not event.is_upcoming())
        ok_(event in Event.objects.live())
        ok_(event in Event.objects.live().approved())

        # now suppose, it as a pending approval on it
        app = Approval.objects.create(event=event)
        ok_(event in Event.objects.live())
        ok_(event not in Event.objects.live().approved())

        # basically, it has been looked at and the answer was no
        app.processed = True
        app.save()
        ok_(event in Event.objects.live())
        ok_(event not in Event.objects.live().approved())

        app.approved = True
        app.save()
        ok_(event in Event.objects.live())
        ok_(event in Event.objects.live().approved())

    def test_upcoming_and_approved(self):
        time_soon = timezone.now() + datetime.timedelta(hours=1)
        event = Event.objects.create(
            status=Event.STATUS_SCHEDULED,
            start_time=time_soon,
        )
        ok_(event.is_upcoming())
        ok_(not event.is_live())
        ok_(event in Event.objects.upcoming())
        ok_(event in Event.objects.upcoming().approved())

        # now suppose, it as a pending approval on it
        app = Approval.objects.create(event=event)
        ok_(event in Event.objects.upcoming())
        ok_(event not in Event.objects.upcoming().approved())

        # basically, it has been looked at and the answer was no
        app.processed = True
        app.save()
        ok_(event in Event.objects.upcoming())
        ok_(event not in Event.objects.upcoming().approved())

        app.approved = True
        app.save()
        ok_(event in Event.objects.upcoming())
        ok_(event in Event.objects.upcoming().approved())


class ForeignKeyTests(DjangoTestCase):

    def _successful_delete(self, obj):
        """Delete an object and ensure it's deleted."""
        model = obj.__class__
        obj.delete()
        remaining = model.objects.filter(id=obj.id).exists()
        ok_(not remaining, 'The object was not deleted.  Model: %s' % model)

    def _refresh_ok(self, obj, exists=True):
        """Ensure that an object still exists or is gone."""
        model = obj.__class__
        refresh = model.objects.filter(id=obj.id).exists()
        if exists:
            ok_(refresh, 'The object no longer exists.  Model: %s' % model)
        else:
            ok_(not refresh, 'The object still exists.  Model: %s' % model)

    def test_template_remove(self):
        """Deleting a Template does not delete associated Event."""
        event = Event.objects.get(id=22)
        self._successful_delete(event.template)
        self._refresh_ok(event)

    def test_location_remove(self):
        """Deleting a Location does not delete associated Event."""
        event = Event.objects.get(id=22)
        self._successful_delete(event.location)
        self._refresh_ok(event)

    def test_channel_remove(self):
        """Deleting a Channel does not delete associated Event."""
        event = Event.objects.get(id=22)
        assert event.channels.all().count()
        for channel in event.channels.all():
            self._successful_delete(channel)
        self._refresh_ok(event)

    def test_user_creator_remove(self):
        """Deleting a creator User does not delete associated Event."""
        event = Event.objects.get(id=22)
        user = User.objects.get(id=1)
        event.creator = user
        event.modified_user = None
        event.save()
        self._successful_delete(user)
        self._refresh_ok(event)

    def test_user_modifier_remove(self):
        """Deleting a modifying User does not delete associated Event."""
        event = Event.objects.get(id=22)
        user = User.objects.get(id=1)
        event.creator = None
        event.modified_user = user
        event.save()
        self._successful_delete(user)
        self._refresh_ok(event)

    def test_eventoldslug_remove(self):
        """Deleting an EventOldSlug does not delete associated Event."""
        event = Event.objects.get(title='Test event')
        oldslug = EventOldSlug.objects.create(
            event=event,
            slug='test-old-slug'
        )
        self._successful_delete(oldslug)
        self._refresh_ok(event)

    def test_group_remove(self):
        """Deleting a Group does not delete associated Approval."""
        event = Event.objects.get(id=22)
        group = Group.objects.create(name='testapprover')
        approval = Approval(event=event, group=group)
        approval.save()
        self._successful_delete(group)
        self._refresh_ok(approval)

    def test_user_remove(self):
        """Deleting a User does not delete associated Approval."""
        event = Event.objects.get(id=22)
        user = User.objects.get(id=1)
        approval = Approval(event=event, user=user)
        approval.save()
        self._successful_delete(user)
        self._refresh_ok(approval)

    def test_approval_remove(self):
        """Deleting an Approval does not delete associated Event."""
        event = Event.objects.get(id=22)
        approval = Approval(event=event)
        approval.save()
        self._successful_delete(approval)
        self._refresh_ok(event)

    def test_tags_remove(self):
        """Deleting all Tags does not delete associated Event."""
        event = Event.objects.get(id=22)
        event.tags.add(Tag.objects.create(name='testing'))
        tags = event.tags.all()
        ok_(tags.exists())
        for tag in tags:
            self._successful_delete(tag)
        self._refresh_ok(event)

    def test_event_remove_approval(self):
        """Deleting an Event DOES remove associated Approval."""
        event = Event.objects.get(id=22)
        approval = Approval(event=event)
        approval.save()
        self._successful_delete(event)
        self._refresh_ok(approval, exists=False)

    def test_event_remove_eventoldslug(self):
        """Deleting an Event DOES remove associated EventOldSlug."""
        event = Event.objects.get(title='Test event')
        oldslug = EventOldSlug.objects.create(
            event=event,
            slug='test-old-slug'
        )
        eq_(oldslug.event, event)
        self._successful_delete(event)
        self._refresh_ok(oldslug, exists=False)


class RecruitmentMessageTests(DjangoTestCase):

    def test_create(self):
        msg = RecruitmentMessage.objects.create(
            text='Check this out',
            url='http://www.com'
        )
        eq_(msg.notes, '')
        ok_(msg.modified)
        ok_(msg.created)

    def test_delete_modified_user(self):
        msg = RecruitmentMessage.objects.create(
            text='Check this out',
            url='http://www.com'
        )
        bob = User.objects.create(username='bob')
        msg.modified_user = bob
        msg.save()
        bob.delete()
        ok_(RecruitmentMessage.objects.all())

    def test_delete_unbreaks_user(self):
        msg = RecruitmentMessage.objects.create(
            text='Check this out',
            url='http://www.com'
        )
        bob = User.objects.create(username='bob')
        eq_(User.objects.all().count(), 2)
        msg.modified_user = bob
        msg.save()
        msg.delete()
        eq_(User.objects.all().count(), 2)

    def test_delete_unbreaks_event(self):
        event = Event.objects.get(title='Test event')
        msg = RecruitmentMessage.objects.create(
            text='Check this out',
            url='http://www.com'
        )
        event.recruitmentmessage = msg
        event.save()
        msg.delete()

        eq_(Event.objects.all().count(), 1)


class PictureTests(DjangoTestCase):

    def test_create_picture(self):
        # the only thing you should need is the picture itself
        with open(self.main_image) as fp:
            picture = Picture.objects.create(file=File(fp))
            ok_(picture.size > 0)
            ok_(picture.width > 0)
            ok_(picture.height > 0)

            ok_(Picture.__name__ in repr(picture))
            picture.notes = "Something"
            ok_("Something" in repr(picture))


class CuratedGroupsTest(DjangoTestCase):

    def test_get_names(self):
        event = Event.objects.get(title='Test event')
        eq_(CuratedGroup.get_names(event), [])

        group1 = CuratedGroup.objects.create(
            event=event,
            name='secrets'
        )
        eq_(CuratedGroup.get_names(event), ['secrets'])

        group2 = CuratedGroup.objects.create(
            event=event,
            name='ABBA fans'
        )
        eq_(CuratedGroup.get_names(event), ['ABBA fans', 'secrets'])

        group1.delete()
        eq_(CuratedGroup.get_names(event), ['ABBA fans'])

        group2.name = 'ABBA Fans'
        group2.save()
        eq_(CuratedGroup.get_names(event), ['ABBA Fans'])


class VidlySubmissionTests(DjangoTestCase):

    def test_get_least_square_slope(self):
        eq_(VidlySubmission.get_least_square_slope(), None)

        event = Event.objects.get(title='Test event')
        event.duration = 300
        event.save()

        now = timezone.now()
        VidlySubmission.objects.create(
            event=event,
            submission_time=now,
            finished=now + datetime.timedelta(seconds=event.duration * 2.1)
        )
        other_event = Event.objects.create(
            duration=450,
            slug='other',
            start_time=event.start_time,
        )
        VidlySubmission.objects.create(
            event=other_event,
            submission_time=now,
            finished=now + datetime.timedelta(
                seconds=other_event.duration * 1.9
            )
        )
        eq_(VidlySubmission.get_least_square_slope(), 1.5)


class VidlyMediaTests(DjangoTestCase):

    @mock.patch('requests.head')
    def test_get_or_create(self, rhead):

        head_requests = []

        def mocked_head(url):
            head_requests.append(url)
            if url == 'http://cdn.vidly/file.mp4':
                return Response('', 302, headers={
                    'Content-Type': 'video/mp5',
                    'Content-Length': '2594479502',
                })
            else:
                return Response('', 302, headers={
                    'Location': 'http://cdn.vidly/file.mp4',
                })

        rhead.side_effect = mocked_head
        information = VidlyMedia.get_or_create(
            'xyz123',
            'mp4',
            True
        )
        eq_(information.tag, 'xyz123')
        eq_(information.video_format, 'mp4')
        eq_(information.hd, True)

        eq_(information.url, 'http://cdn.vidly/file.mp4')
        eq_(information.content_type, 'video/mp5')
        eq_(information.size, 2594479502L)

        assert len(head_requests) == 2

        # do it again,
        same_information = VidlyMedia.get_or_create(
            'xyz123',
            'mp4',
            True
        )
        eq_(same_information, information)
        assert len(head_requests) == 2

    def test_get_or_create_multiples(self):

        first = VidlyMedia.objects.create(
            tag='xyz123',
            hd=True,
            video_format='mp4',
            url='http://first.com',
            size=10000,
            content_type='video/mp4'
        )
        information = VidlyMedia.get_or_create(
            'xyz123',
            'mp4',
            True
        )
        eq_(information, first)

        # Because the creation of these can happen in non-atomic views
        # (ie. rendering the itunes feed), you might get a race condition
        # in creating these so there might be multiples.
        # The classmethod get_or_create (not to be confused with
        # objects.get_or_create()) needs to be resilient to this.
        second = VidlyMedia.objects.create(
            tag='xyz123',
            hd=True,
            video_format='mp4',
            url='http://second.com',
            size=10001,
            content_type='video/mp4'
        )
        information = VidlyMedia.get_or_create(
            'xyz123',
            'mp4',
            True
        )
        eq_(information, second)
