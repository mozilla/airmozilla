from nose.tools import eq_

from django.test import TestCase
from django.contrib.auth.models import User

from airmozilla.manage import forms
from airmozilla.main.models import (
    Event,
    EventAssignment,
    Location
)


class TestForms(TestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']

    def test_event_assignment_form(self):
        event = Event.objects.get(title='Test event')
        user, = User.objects.all()
        user.is_active = False
        user.save()

        barcelona = Location.objects.create(name='Barcelona')
        alf = User.objects.create(
            username='alf',
            email='alf@email.com',
            first_name='Alf'
        )
        zorro = User.objects.create(
            username='zorro',
            email='Zorro@email.com',
        )

        assignment = EventAssignment.objects.create(event=event)
        form = forms.EventAssignmentForm(instance=assignment)
        eq_(form.fields['locations'].choices, [(barcelona.pk, barcelona.name)])
        eq_(
            form.fields['users'].choices,
            [
                (alf.pk, 'alf@email.com (Alf)'),
                (zorro.pk, u'Zorro@email.com')
            ]
        )
