import json

from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse

from airmozilla.main.models import Tag, Event
from .base import ManageTestCase


class TestTags(ManageTestCase):
    def test_tags(self):
        """Tag management pages return successfully."""
        response = self.client.get(reverse('manage:tags'))
        eq_(response.status_code, 200)

    def test_tags_data(self):
        Tag.objects.create(name='testing')
        url = reverse('manage:tags_data')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        content = json.loads(response.content)
        ok_(content['tags'])
        ok_(content['urls'])
        eq_(
            content['urls']['manage:tag_edit'],
            reverse('manage:tag_edit', args=('0',))
        )
        eq_(
            content['urls']['manage:tag_remove'],
            reverse('manage:tag_remove', args=('0',))
        )

    def test_tag_remove(self):
        """Removing a tag works correctly and leaves associated events
           with null tags."""
        event = Event.objects.get(id=22)
        tag = Tag.objects.create(name='testing')
        event.tags.add(tag)
        assert tag in event.tags.all()
        event.tags.add(Tag.objects.create(name='othertag'))
        eq_(event.tags.all().count(), 2)
        self._delete_test(tag, 'manage:tag_remove', 'manage:tags')
        event = Event.objects.get(id=22)
        eq_(event.tags.all().count(), 1)

    def test_tag_edit(self):
        """Test tag editor; timezone switch works correctly."""
        tag = Tag.objects.create(name='testing')
        url = reverse('manage:tag_edit', kwargs={'id': tag.id})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response = self.client.post(url, {
            'name': 'different',
        })
        self.assertRedirects(response, reverse('manage:tags'))
        tag = Tag.objects.get(id=tag.id)
        eq_(tag.name, 'different')

        Tag.objects.create(name='alreadyinuse')
        response = self.client.post(url, {
            'name': 'ALREADYINUSE',
        })
        eq_(response.status_code, 200)
        ok_('Used by another tag' in response.content)

    def test_tag_merge_repeated(self):
        t1 = Tag.objects.create(name='Tagg')
        t2 = Tag.objects.create(name='TaGG')
        t3 = Tag.objects.create(name='tAgg')

        event = Event.objects.get(title='Test event')
        event.tags.add(t1)

        event2 = Event.objects.create(
            title='Other Title',
            start_time=event.start_time,
        )
        event2.tags.add(t1)
        event2.tags.add(t2)
        event3 = Event.objects.create(
            title='Other Title Again',
            start_time=event.start_time,
        )
        event3.tags.add(t2)
        event3.tags.add(t3)

        # t1 is now repeated
        edit_url = reverse('manage:tag_edit', args=(t1.id,))
        response = self.client.get(edit_url)
        eq_(response.status_code, 200)

        merge_url = reverse('manage:tag_merge_repeated', args=(t1.id,))
        ok_(merge_url in response.content)
        response = self.client.post(merge_url, {'keep': t2.id})
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('manage:tags')
        )

        eq_(Tag.objects.filter(name__iexact='TAGG').count(), 1)
        eq_(Tag.objects.filter(name='TaGG').count(), 1)
        eq_(Tag.objects.filter(name='Tagg').count(), 0)
        eq_(Tag.objects.filter(name='tAgg').count(), 0)

        eq_(Event.objects.filter(tags__name='TaGG').count(), 3)
        eq_(Event.objects.filter(tags__name='Tagg').count(), 0)
        eq_(Event.objects.filter(tags__name='tAgg').count(), 0)

    def test_tag_merge(self):
        t1 = Tag.objects.create(name='Tagg')
        event = Event.objects.get(title='Test event')
        event.tags.add(t1)

        t2 = Tag.objects.create(name='Other')
        event.tags.add(t2)

        # Now suppose you want to only use the 'Other' tag and
        # move all tags called 'Tagg' to that.
        url = reverse('manage:tag_merge', args=(t1.id,))
        # But before we do that, let's make a typo!
        response = self.client.post(url, {'name': 'UTHER'})
        eq_(response.status_code, 400)
        # Now let's spell it correctly
        response = self.client.post(url, {'name': 'OTHER'})
        eq_(response.status_code, 302)

        ok_(not Tag.objects.filter(name__iexact='Tagg'))
        eq_(list(event.tags.all()), list(Tag.objects.filter(name='Other')))
