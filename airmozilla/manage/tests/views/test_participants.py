from nose.tools import eq_, ok_

from funfactory.urlresolvers import reverse

from airmozilla.main.models import Participant
from .base import ManageTestCase


class TestParticipants(ManageTestCase):
    def test_participant_pages(self):
        """Participants pagination always returns valid pages."""
        response = self.client.get(reverse('manage:participants'))
        eq_(response.status_code, 200)
        response = self.client.get(reverse('manage:participants'),
                                   {'page': 5000})
        eq_(response.status_code, 200)

    def test_participant_find(self):
        """Search filters participants; returns all for bad search."""
        response_ok = self.client.post(
            reverse('manage:participants'),
            {
                'name': 'Tim'
            }
        )
        eq_(response_ok.status_code, 200)
        ok_(response_ok.content.find('Tim') >= 0)
        response_fail = self.client.post(
            reverse('manage:participants'),
            {
                'name': 'Lincoln'
            }
        )
        eq_(response_fail.status_code, 200)
        ok_(response_fail.content.find('Tim') >= 0)

    def test_participant_edit(self):
        """Participant edit page responds OK; bad form results in failure;
        submission induces a change.
        """
        participant = Participant.objects.get(name='Tim Mickel')
        response = self.client.get(reverse('manage:participant_edit',
                                           kwargs={'id': participant.id}))
        eq_(response.status_code, 200)
        response_ok = self.client.post(
            reverse('manage:participant_edit', kwargs={'id': participant.id}),
            {
                'name': 'George Washington',
                'email': 'george@whitehouse.gov',
                'role': Participant.ROLE_PRINCIPAL_PRESENTER,
                'cleared': Participant.CLEARED_YES
            }
        )
        self.assertRedirects(response_ok, reverse('manage:participants'))
        participant_george = Participant.objects.get(id=participant.id)
        eq_(participant_george.name, 'George Washington')
        response_fail = self.client.post(
            reverse('manage:participant_edit', kwargs={'id': participant.id}),
            {
                'name': 'George Washington',
                'email': 'bademail'
            }
        )
        eq_(response_fail.status_code, 200)

    def test_participant_email(self):
        """Participant email page generates a token, redirects properly."""
        participant = Participant.objects.get(name='Tim Mickel')
        participant.clear_token = ''
        participant.save()
        url = reverse('manage:participant_email',
                      kwargs={'id': participant.id})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        participant = Participant.objects.get(name='Tim Mickel')
        ok_(participant.clear_token)
        response_redirect = self.client.post(url)
        self.assertRedirects(response_redirect, reverse('manage:participants'))

    def test_participant_new(self):
        """New participant page responds OK and form works as expected."""
        response = self.client.get(reverse('manage:participant_new'))
        eq_(response.status_code, 200)
        with open('airmozilla/manage/tests/firefox.png') as fp:
            response_ok = self.client.post(
                reverse('manage:participant_new'),
                {
                    'name': 'Mozilla Firefox',
                    'slug': 'mozilla-firefox',
                    'photo': fp,
                    'email': 'mozilla@mozilla.com',
                    'role': Participant.ROLE_PRINCIPAL_PRESENTER,
                    'cleared': Participant.CLEARED_NO
                }
            )
        self.assertRedirects(response_ok, reverse('manage:participants'))
        participant = Participant.objects.get(name='Mozilla Firefox')
        eq_(participant.email, 'mozilla@mozilla.com')
        eq_(participant.creator, self.user)

    def test_participant_remove(self):
        participant = Participant.objects.get(name='Tim Mickel')
        self._delete_test(participant, 'manage:participant_remove',
                          'manage:participants')
