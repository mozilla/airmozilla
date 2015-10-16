from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse

from airmozilla.main.models import RecruitmentMessage
from .base import ManageTestCase


class TestRecruitmentMessages(ManageTestCase):

    def test_recruitmentmessages(self):
        response = self.client.get(reverse('manage:recruitmentmessages'))
        eq_(response.status_code, 200)

    def test_recruitmentmessage_new(self):
        url = reverse('manage:recruitmentmessage_new')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response = self.client.post(url, {
            'text': 'Web Developer',
            'url': 'http://careers.mozilla.com/123',
            'active': True,
            'notes': 'Some notes'
        })
        self.assertRedirects(response, reverse('manage:recruitmentmessages'))
        ok_(RecruitmentMessage.objects.get(text='Web Developer'))
        response_fail = self.client.post(url)
        eq_(response_fail.status_code, 200)

    def test_recruitmentmessage_edit(self):
        msg = RecruitmentMessage.objects.create(
            text='Web Developer',
            url='http://careers.mozilla.com/123',
            active=True,
            notes='Some notes'
        )
        url = reverse('manage:recruitmentmessage_edit', args=(msg.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response = self.client.post(url, {
            'text': 'Senior Web Developer',
            'url': 'http://careers.mozilla.com/456',
            'notes': 'other notes',
        })
        self.assertRedirects(response, reverse('manage:recruitmentmessages'))
        msg = RecruitmentMessage.objects.get(id=msg.id)
        eq_(msg.text, 'Senior Web Developer')
        eq_(msg.url, 'http://careers.mozilla.com/456')
        ok_(not msg.active)
        eq_(msg.notes, 'other notes')
        response_fail = self.client.post(url, {
            'text': 'Web Developer'
        })
        eq_(response_fail.status_code, 200)

    def test_recruitmentmessage_delete(self):
        msg = RecruitmentMessage.objects.create(
            text='Web Developer',
            url='http://careers.mozilla.com/123',
        )
        self._delete_test(
            msg,
            'manage:recruitmentmessage_delete',
            'manage:recruitmentmessages'
        )
