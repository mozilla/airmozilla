from django.contrib.auth.models import Group, User
from django.test import TestCase

from nose.tools import ok_, eq_

from airmozilla.main.models import Approval, Event, EventOldSlug


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

    def test_category_remove(self):
        """Deleting a Category does not delete associated Event."""
        event = Event.objects.get(id=22)
        self._successful_delete(event.category)
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
        event = Event.objects.get(id=22)
        oldslug = EventOldSlug.objects.get(id=1)
        ok_(oldslug)
        eq_(oldslug.event, event)
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

    def test_participants_remove(self):
        """Deleting all Participants does not delete associated Event."""
        event = Event.objects.get(id=22)
        participants = event.participants.all()
        ok_(participants.exists())
        for participant in participants:
            self._successful_delete(participant)
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
        event = Event.objects.get(id=22)
        oldslug = EventOldSlug.objects.get(id=1)
        eq_(oldslug.event, event)
        self._successful_delete(event)
        self._refresh_ok(oldslug, exists=False)
