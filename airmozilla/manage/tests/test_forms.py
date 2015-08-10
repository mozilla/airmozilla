from nose.tools import eq_, ok_

from django.contrib.auth.models import User

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.manage import forms
from airmozilla.main.models import (
    Event,
    EventAssignment,
    Location
)


class TestForms(DjangoTestCase):

    def test_event_assignment_form(self):
        event = Event.objects.get(title='Test event')
        user, = User.objects.all()
        user.is_active = False
        user.save()

        barcelona = Location.objects.create(name='Barcelona')
        alf = User.objects.create(
            username='alf',
            email='alf@email.com',
            first_name='Alf',
            is_staff=True
        )
        zorro = User.objects.create(
            username='zorro',
            email='Zorro@email.com',
            is_staff=True
        )
        carlos = User.objects.create(
            username='carlos',
            email='carlos@email.com'
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
        ok_(
            (carlos.pk, 'carlos@email.com') not in form.fields['users'].choices
            )
