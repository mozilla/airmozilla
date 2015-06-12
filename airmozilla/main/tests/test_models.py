import datetime

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.utils import timezone
from django.utils.timezone import utc
from django.core.files import File

from nose.tools import ok_, eq_

from airmozilla.main.models import (
    Approval,
    Event,
    EventOldSlug,
    Location,
    most_recent_event,
    RecruitmentMessage,
    Picture,
    CuratedGroup,
    VidlySubmission
)
# This must be imported otherwise django-nose won't import
# that foreign key reference when you run only the tests in this file.
from airmozilla.uploads.models import Upload
Upload = Upload  # shut up pyflakes


class EventTests(TestCase):

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


class EventStateTests(TestCase):
    # def test_event_state(self):
    #     time_now = timezone.now()
    #     time_soon = time_now + datetime.timedelta(hours=1)
    #     time_before = time_now - datetime.timedelta(hours=1)
    #     # initiated event
    #     initiated = Event.objects.create(
    #         status=Event.STATUS_INITIATED,
    #         start_time=time_now,
    #     )
    #     # ok_(initiated in Event.objects.initiated())
    #     ok_(not initiated.needs_approval())
    #     # scheduled event with pending approval
    #     to_approve = Event.objects.create(
    #         status=Event.STATUS_SCHEDULED,
    #         start_time=time_now,
    #     )
    #     # ok_(to_approve not in Event.objects.initiated())
    #     ok_(to_approve in Event.approved_objects.all())
    #     ok_(not to_approve.needs_approval())
    #
    #     app = Approval.objects.create(event=to_approve, group=None)
    #     # attaching the Approval makes the event unapproved
    #     ok_(to_approve not in Event.approved_objects.all())
    #     # ok_(to_approve in Event.objects.initiated())
    #     ok_(to_approve.needs_approval())
    #
    #     app.processed = True
    #     app.approved = True
    #     app.save()
    #     ok_(to_approve in Event.approved_objects.all())
    #     to_approve.status = Event.STATUS_REMOVED
    #     to_approve.save()
    #     # ok_(to_approve in Event.objects.archived_and_removed())
    #     # ok_(to_approve not in Event.objects.initiated())
    #     # upcoming event
    #     upcoming = Event.objects.create(
    #         status=Event.STATUS_SCHEDULED,
    #         start_time=time_soon,
    #         archive_time=None
    #     )
    #     ok_(upcoming in Event.approved_objects.upcoming())
    #     ok_(upcoming in Event.objects.upcoming())
    #     upcoming.status = Event.STATUS_REMOVED
    #     upcoming.save()
    #     # ok_(upcoming in Event.objects.archived_and_removed())
    #     ok_(upcoming not in Event.objects.upcoming())
    #     # live event
    #     live = Event.objects.create(
    #         status=Event.STATUS_SCHEDULED,
    #         start_time=time_now,
    #         archive_time=None
    #     )
    #     ok_(live in Event.approved_objects.live())
    #     ok_(live in Event.objects.live())
    #     live.status = Event.STATUS_REMOVED
    #     live.save()
    #     # ok_(live in Event.objects.archived_and_removed())
    #     ok_(live not in Event.objects.live())
    #     # archiving event
    #     archiving = Event.objects.create(
    #         status=Event.STATUS_SCHEDULED,
    #         start_time=time_before,
    #         archive_time=time_soon
    #     )
    #     ok_(archiving in Event.approved_objects.all())
    #     # ok_(archiving in Event.objects.archiving())
    #     ok_(archiving not in Event.objects.live())
    #     archiving.status = Event.STATUS_REMOVED
    #     archiving.save()
    #     # ok_(archiving in Event.objects.archived_and_removed())
    #     # ok_(archiving not in Event.objects.archiving())
    #     # archived event
    #     archived = Event.objects.create(
    #         status=Event.STATUS_SCHEDULED,
    #         start_time=time_before,
    #         archive_time=time_before
    #     )
    #     ok_(archived in Event.approved_objects.archived())
    #     ok_(archived in Event.objects.archived())
    #     archived.status = Event.STATUS_REMOVED
    #     archived.save()
    #     # ok_(archived in Event.objects.archived_and_removed())
    #     ok_(archived not in Event.objects.archived())

    # def test_needs_approval_if_not_approved(self):
    #     time_now = timezone.now()
    #     to_approve = Event.objects.create(
    #         status=Event.STATUS_SCHEDULED,
    #         start_time=time_now,
    #     )
    #     app = Approval.objects.create(event=to_approve, group=None)
    #     ok_(to_approve.needs_approval())
    #     app.processed = True
    #     app.save()
    #     ok_(not to_approve.needs_approval())

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


class ForeignKeyTests(TestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']

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
        group = Group.objects.get(id=1)
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


class RecruitmentMessageTests(TestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']

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


class PictureTests(TestCase):
    main_image = 'airmozilla/manage/tests/firefox.png'

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


class CuratedGroupsTest(TestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']

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


class VidlySubmissionTests(TestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']

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
