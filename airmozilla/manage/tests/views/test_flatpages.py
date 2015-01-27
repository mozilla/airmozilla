from nose.tools import eq_, ok_

from django.conf import settings
from django.contrib.sites.models import Site
from django.contrib.flatpages.models import FlatPage

from funfactory.urlresolvers import reverse

from airmozilla.main.models import Event, Channel
from .base import ManageTestCase


class TestFlatPages(ManageTestCase):

    def setUp(self):
        super(TestFlatPages, self).setUp()
        FlatPage.objects.create(
            url='/my-page',
            title='Test page',
            content='<p>Test content</p>',
        ).sites.add(Site.objects.get(id=1))

    def test_flatpages(self):
        response = self.client.get(reverse('manage:flatpages'))
        eq_(response.status_code, 200)

    def test_flatpage_new(self):
        url = reverse('manage:flatpage_new')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_ok = self.client.post(url, {
            'url': '/cool-page',
            'title': 'Cool title',
            'content': '<h4>Hello</h4>'
        })
        self.assertRedirects(response_ok, reverse('manage:flatpages'))
        flatpage = FlatPage.objects.get(url='/cool-page')
        ok_(flatpage)
        site, = flatpage.sites.all()
        eq_(site.pk, settings.SITE_ID)
        response_fail = self.client.post(url)
        eq_(response_fail.status_code, 200)

    def test_flatpage_edit(self):
        flatpage = FlatPage.objects.get(title='Test page')
        url = reverse('manage:flatpage_edit', kwargs={'id': flatpage.id})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_ok = self.client.post(url, {
            'url': flatpage.url,
            'title': 'New test page',
            'content': '<p>New content</p>'
        })
        self.assertRedirects(response_ok, reverse('manage:flatpages'))
        flatpage = FlatPage.objects.get(id=flatpage.id)
        eq_(flatpage.content, '<p>New content</p>')
        response_fail = self.client.post(url, {
            'url': 'no title',
        })
        eq_(response_fail.status_code, 200)

    def test_flatpage_remove(self):
        flatpage = FlatPage.objects.get(title='Test page')
        self._delete_test(flatpage, 'manage:flatpage_remove',
                          'manage:flatpages')

    def test_view_flatpage(self):
        flatpage = FlatPage.objects.get(title='Test page')
        response = self.client.get('/pages%s' % flatpage.url)
        eq_(response.status_code, 200)
        ok_('Test page' in response.content)

    def test_flatpage_new_with_sidebar(self):
        url = reverse('manage:flatpage_new')
        # not split by at least 2 `_`
        response_fail = self.client.post(url, {
            'url': 'sidebar_incorrectformat',
            'title': 'whatever',
            'content': '<h4>Hello</h4>'
        })
        eq_(response_fail.status_code, 200)
        ok_('Form errors!' in response_fail.content)

        # unrecognized slug
        response_fail = self.client.post(url, {
            'url': 'sidebar_east_never_heard_of',
            'title': 'whatever',
            'content': '<h4>Hello</h4>'
        })
        eq_(response_fail.status_code, 200)
        ok_('Form errors!' in response_fail.content)

        Channel.objects.create(
            name='Heard Of',
            slug='heard_of'
        )

        # should work now
        response_ok = self.client.post(url, {
            'url': 'sidebar_east_heard_of',
            'title': 'whatever',
            'content': '<h4>Hello</h4>'
        })
        self.assertRedirects(response_ok, reverse('manage:flatpages'))

        flatpage = FlatPage.objects.get(
            url='sidebar_east_heard_of'
        )
        # the title would automatically become auto generated
        ok_('Heard Of' in flatpage.title)

    def test_flatpage_edit_with_sidebar(self):
        flatpage = FlatPage.objects.get(title='Test page')
        url = reverse('manage:flatpage_edit', kwargs={'id': flatpage.id})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_ok = self.client.post(url, {
            'url': 'sidebar_bottom_main',
            'title': 'New test page',
            'content': '<p>New content</p>'
        })
        self.assertRedirects(response_ok, reverse('manage:flatpages'))
        flatpage = FlatPage.objects.get(id=flatpage.id)
        eq_(flatpage.content, '<p>New content</p>')
        eq_('Sidebar (bottom) Main', flatpage.title)

    def test_flatpage_with_url_that_clashes(self):
        event = Event.objects.get(slug='test-event')
        FlatPage.objects.create(
            url='/' + event.slug,
            title='Some Page',
        )
        response = self.client.get(reverse('manage:flatpages'))
        eq_(response.status_code, 200)
        # there should now be a link to event it clashes with
        ok_('/pages/%s' % event.slug in response.content)
        event_url = reverse('main:event', args=(event.slug,))
        ok_(event_url in response.content)
