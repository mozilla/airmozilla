from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse

from airmozilla.main.models import Channel

from .base import ManageTestCase


class TestChannels(ManageTestCase):
    def setUp(self):
        super(TestChannels, self).setUp()
        Channel.objects.create(
            name='Testing',
            slug='testing',
            description='Anything'
        )

    def test_channels(self):
        """ Channels listing responds OK. """
        response = self.client.get(reverse('manage:channels'))
        eq_(response.status_code, 200)

        # list again when one of them is a YouTube channel
        channel = Channel.objects.create(
            name='SXSW',
            slug='sxsw',
            youtube_id='x1x2x3x4'
        )

        response = self.client.get(reverse('manage:channels'))
        eq_(response.status_code, 200)
        ok_(channel.youtube_url in response.content)

    def test_channel_new(self):
        """ Channel form adds new channels. """
        # render the form
        response = self.client.get(reverse('manage:channel_new'))
        eq_(response.status_code, 200)

        response_ok = self.client.post(
            reverse('manage:channel_new'),
            {
                'name': ' Web Dev ',
                'slug': 'web-dev',
                'description': '<h1>Stuff</h1>',
                'image_is_banner': True,
                'feed_size': 10,
            }
        )
        self.assertRedirects(response_ok, reverse('manage:channels'))
        ok_(Channel.objects.get(name='Web Dev'))
        ok_(Channel.objects.get(name='Web Dev').image_is_banner)
        response_fail = self.client.post(reverse('manage:channel_new'))
        eq_(response_fail.status_code, 200)

    def test_channel_edit(self):
        channel = Channel.objects.get(slug='testing')
        response = self.client.get(
            reverse('manage:channel_edit', args=(channel.pk,)),
        )
        eq_(response.status_code, 200)
        ok_('value="testing"' in response.content)
        response = self.client.post(
            reverse('manage:channel_edit', args=(channel.pk,)),
            {
                'name': 'Different',
                'slug': 'different',
                'description': '<p>Other things</p>',
                'feed_size': 10,
            }
        )
        eq_(response.status_code, 302)
        channel = Channel.objects.get(slug='different')

    def test_channel_edit_visibility_clash(self):
        channel = Channel.objects.get(slug='testing')
        response = self.client.get(
            reverse('manage:channel_edit', args=(channel.pk,)),
        )
        response = self.client.post(
            reverse('manage:channel_edit', args=(channel.pk,)),
            {
                'name': 'Different',
                'slug': 'different',
                'description': '<p>Other things</p>',
                'never_show': True,
                'always_show': True,
                'feed_size': 10,
            }
        )
        eq_(response.status_code, 200)

    def test_channel_edit_child(self):
        channel = Channel.objects.get(slug='testing')
        response = self.client.get(
            reverse('manage:channel_edit', args=(channel.pk,)),
        )
        eq_(response.status_code, 200)
        choices = (
            response.content
            .split('name="parent"')[1]
            .split('</select>')[0]
        )
        ok_('Main' in choices)
        # you should not be able to self-reference
        ok_('Testing' not in choices)

        main = Channel.objects.get(slug='main')
        response = self.client.post(
            reverse('manage:channel_edit', args=(channel.pk,)),
            {
                'name': 'Different',
                'slug': 'different',
                'description': '<p>Other things</p>',
                'parent': main.pk,
                'feed_size': 10,
            }
        )
        eq_(response.status_code, 302)
        channel = Channel.objects.get(slug='different')
        eq_(channel.parent, main)

        # now expect two links to "Main" on the channels page
        response = self.client.get(reverse('manage:channels'))
        eq_(response.status_code, 200)
        view_url = reverse('main:home_channels', args=(main.slug,))
        eq_(response.content.count(view_url), 2)

    def test_channel_delete(self):
        channel = Channel.objects.create(
            name='How Tos',
            slug='how-tos',
        )
        self._delete_test(channel, 'manage:channel_remove',
                          'manage:channels')
