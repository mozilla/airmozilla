from nose.tools import eq_, ok_

from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse

from airmozilla.main.models import Topic
from .base import ManageTestCase


class TestTopics(ManageTestCase):

    def test_topics(self):
        Topic.objects.create(topic='New Topic')
        response = self.client.get(reverse('manage:topics'))
        eq_(response.status_code, 200)
        ok_('New Topic' in response.content)

    def test_topic_new(self):
        url = reverse('manage:topic_new')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        group1 = Group.objects.create(name='PR')
        group2 = Group.objects.create(name='Legal')
        response_ok = self.client.post(url, {
            'topic': 'testing',
            'sort_order': 0,
            'groups': [group1.id, group2.id],
            'is_active': True,
        })
        self.assertRedirects(response_ok, reverse('manage:topics'))

        response_fail = self.client.post(url)
        eq_(response_fail.status_code, 200)
        ok_('This field is required' in response_fail.content)

        topic = Topic.objects.get(topic='testing', is_active=True)
        ok_(group1 in topic.groups.all())
        ok_(group2 in topic.groups.all())

    def test_topic_remove(self):
        topic = Topic.objects.create(
            topic="Something"
        )
        self._delete_test(
            topic,
            'manage:topic_remove',
            'manage:topics'
        )
        assert not Topic.objects.filter(topic="Something")

    def test_topic_edit(self):
        """Test topic editor"""
        topic = Topic.objects.create(topic='Partnership Things')
        url = reverse('manage:topic_edit', kwargs={'id': topic.id})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Partnership Things' in response.content)

        group = Group.objects.create(name='PR')
        response = self.client.post(url, {
            'topic': 'Business Things',
            'groups': [group.id],
            'sort_order': 1,
        })
        self.assertRedirects(response, reverse('manage:topics'))
        ok_(Topic.objects.get(topic='Business Things'))

    def test_topics_inactive(self):
        Topic.objects.create(topic='New Topic', is_active=False)
        response = self.client.get(reverse('manage:topics'))
        eq_(response.status_code, 200)
        ok_("Inactive topic" in response.content)
