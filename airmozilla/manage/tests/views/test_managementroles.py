from nose.tools import eq_, ok_

from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse

from airmozilla.main.models import Event
from .base import ManageTestCase


class TestManagementRoles(ManageTestCase):
    """Basic tests to ensure management roles / permissions are working."""
    fixtures = ManageTestCase.fixtures + [
        'airmozilla/manage/tests/manage_groups_testdata.json'
    ]

    def setUp(self):
        super(TestManagementRoles, self).setUp()
        self.user.is_superuser = False
        self.user.save()

    def _add_client_group(self, name):
        group = Group.objects.get(name=name)
        group.user_set.add(self.user)
        ok_(group in self.user.groups.all())

    def test_producer(self):
        """Producer can see fixture events and edit pages."""
        self._add_client_group('Producer')
        response_events = self.client.get(reverse('manage:events_data'))
        eq_(response_events.status_code, 200)
        ok_('Test event' in response_events.content)

    def _unprivileged_event_manager_tests(self, form_contains,
                                          form_not_contains):
        """Common tests for organizers/experienced organizers to ensure
           basic event permissions are not violated."""
        response_event_request = self.client.get(
            reverse('manage:event_request')
        )
        eq_(response_event_request.status_code, 200)
        ok_(form_contains in response_event_request.content)
        ok_(form_not_contains not in response_event_request.content)
        response_events = self.client.get(reverse('manage:events_data'))
        eq_(response_events.status_code, 200)
        ok_('Test event' not in response_events.content,
            'Unprivileged viewer can see events which do not belong to it')
        event = Event.objects.get(title='Test event')
        event.creator = self.user
        event.save()
        response_events = self.client.get(reverse('manage:events_data'))
        ok_('Test event' in response_events.content,
            'Unprivileged viewer cannot see events which belong to it.')
        response_event_edit = self.client.get(reverse('manage:event_edit',
                                                      kwargs={'id': event.id}))
        ok_(form_contains in response_event_edit.content)
        ok_(form_not_contains not in response_event_edit.content)

    def _unprivileged_page_tests(self, additional_pages=[]):
        """Common tests to ensure unprivileged admins do not have access to
           event or user configuration pages."""
        pages = additional_pages + [
            'manage:users',
            'manage:groups',
            'manage:locations',
            'manage:templates'
        ]
        for page in pages:
            response = self.client.get(reverse(page))
            self.assertRedirects(
                response,
                reverse('manage:insufficient_permissions')
            )

    def test_event_organizer(self):
        """Event organizer: ER with unprivileged form, can only edit own
           and can only see own events."""
        self._add_client_group('Event Organizer')
        self._unprivileged_event_manager_tests(
            form_contains='Start time',  # EventRequestForm
            form_not_contains='Approvals'
        )
        self._unprivileged_page_tests(additional_pages=['manage:approvals'])

    def test_experienced_event_organizer(self):
        """Experienced event organizer: ER with semi-privileged form,
           can only edit own, can only see own events."""
        self._add_client_group('Experienced Event Organizer')
        self._unprivileged_event_manager_tests(
            form_contains='Approvals',  # EventExperiencedRequestForm
            form_not_contains='Featured'
        )
        self._unprivileged_page_tests(additional_pages=['manage:approvals'])

    def test_approver(self):
        """Approver (in this case, PR), can access the approval pages."""
        self._add_client_group('PR')
        self._unprivileged_page_tests(
            additional_pages=['manage:event_request', 'manage:events']
        )
        response_approvals = self.client.get(reverse('manage:approvals'))
        eq_(response_approvals.status_code, 200)

    def test_redirect_to_insufficient_permissions(self):
        """If you're a staff user but lacking a certain permission
        there are certain pages you can't go to and they should redirect
        you to the insufficient_permissions page with a note about which
        permission is missing."""

        url = reverse('manage:insufficient_permissions')
        assert self.user.is_staff
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # now try to access a page you don't have access to
        event = Event.objects.get(title='Test event')
        uploads_url = reverse('manage:event_upload', args=(event.pk,))
        response = self.client.get(uploads_url)
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            url
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        # the permission needed for that URL was called...
        ok_('Can add upload' in response.content)
