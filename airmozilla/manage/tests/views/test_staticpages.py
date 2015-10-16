from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse

from airmozilla.main.models import Event, Channel
from airmozilla.staticpages.models import StaticPage
from .base import ManageTestCase


class TestStaticPages(ManageTestCase):

    def setUp(self):
        super(TestStaticPages, self).setUp()
        StaticPage.objects.create(
            url='/my-page',
            title='Test page',
            content='<p>Test content</p>',
        )

    def test_staticpages(self):
        response = self.client.get(reverse('manage:staticpages'))
        eq_(response.status_code, 200)

    def test_staticpage_new(self):
        url = reverse('manage:staticpage_new')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_ok = self.client.post(url, {
            'url': '/cool-page',
            'title': 'Cool title',
            'content': '<h4>Hello</h4>',
            'privacy': Event.PRIVACY_PUBLIC,
        })
        self.assertRedirects(response_ok, reverse('manage:staticpages'))
        staticpage = StaticPage.objects.get(url='/cool-page')
        ok_(staticpage)
        eq_(staticpage.headers, {})
        response_fail = self.client.post(url)
        eq_(response_fail.status_code, 200)

    def test_staticpage_new_custom_headers(self):
        url = reverse('manage:staticpage_new')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        data = {
            'url': '/cool-page',
            'title': 'Cool title',
            'content': '<h4>Hello</h4>',
            'privacy': Event.PRIVACY_PUBLIC,
        }
        response = self.client.post(url, dict(
            data,
            headers="""
            Key: Value
            Singleword
            """
        ))
        eq_(response.status_code, 200)
        ok_('Form errors' in response.content)
        response = self.client.post(url, dict(
            data,
            headers="""
            Key: Value

            Other: thing
            """
        ))
        eq_(response.status_code, 302)
        staticpage = StaticPage.objects.get(url='/cool-page')
        eq_(staticpage.headers, {
            'Key': 'Value',
            'Other': 'thing'
        })

    def test_staticpage_edit(self):
        staticpage = StaticPage.objects.get(title='Test page')
        url = reverse('manage:staticpage_edit', kwargs={'id': staticpage.id})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_ok = self.client.post(url, {
            'url': staticpage.url,
            'title': 'New test page',
            'content': '<p>New content</p>',
            'privacy': Event.PRIVACY_CONTRIBUTORS,
            # 'headers': '',
        })
        self.assertRedirects(response_ok, reverse('manage:staticpages'))
        staticpage = StaticPage.objects.get(id=staticpage.id)
        eq_(staticpage.content, '<p>New content</p>')
        eq_(staticpage.privacy, Event.PRIVACY_CONTRIBUTORS)
        response_fail = self.client.post(url, {
            'url': 'no title',
            # 'headers': ''
        })
        eq_(response_fail.status_code, 200)

    def test_staticpage_edit_custom_headers(self):
        staticpage = StaticPage.objects.get(title='Test page')
        staticpage.headers = {
            'Key': 'Value',
        }
        staticpage.save()
        url = reverse('manage:staticpage_edit', kwargs={'id': staticpage.id})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Key: Value' in response.content)

        data = {
            'url': staticpage.url,
            'title': 'New test page',
            'content': '<p>New content</p>',
            'privacy': Event.PRIVACY_CONTRIBUTORS,
        }
        response = self.client.post(url, dict(
            data,
            headers=" Singleword ",
        ))
        eq_(response.status_code, 200)
        ok_('Form errors' in response.content)

        response = self.client.post(url, dict(
            data,
            headers=" Custom: Value ",
        ))
        self.assertRedirects(response, reverse('manage:staticpages'))
        staticpage = StaticPage.objects.get(id=staticpage.id)
        eq_(staticpage.headers, {'Custom': 'Value'})

    def test_staticpage_remove(self):
        staticpage = StaticPage.objects.get(title='Test page')
        self._delete_test(staticpage, 'manage:staticpage_remove',
                          'manage:staticpages')

    def test_view_staticpage(self):
        staticpage = StaticPage.objects.get(title='Test page')
        response = self.client.get('/pages%s' % staticpage.url)
        eq_(response.status_code, 200)
        ok_('Test page' in response.content)

    def test_staticpage_new_with_sidebar(self):
        url = reverse('manage:staticpage_new')
        # not split by at least 2 `_`
        response_fail = self.client.post(url, {
            'url': 'sidebar_incorrectformat',
            'title': 'whatever',
            'content': '<h4>Hello</h4>',
            'privacy': Event.PRIVACY_PUBLIC,
        })
        eq_(response_fail.status_code, 200)
        ok_('Form errors!' in response_fail.content)

        # unrecognized slug
        response_fail = self.client.post(url, {
            'url': 'sidebar_east_never_heard_of',
            'title': 'whatever',
            'content': '<h4>Hello</h4>',
            'privacy': Event.PRIVACY_PUBLIC,
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
            'content': '<h4>Hello</h4>',
            'privacy': Event.PRIVACY_PUBLIC,
        })
        self.assertRedirects(response_ok, reverse('manage:staticpages'))

        staticpage = StaticPage.objects.get(
            url='sidebar_east_heard_of'
        )
        # the title would automatically become auto generated
        ok_('Heard Of' in staticpage.title)

    def test_staticpage_edit_with_sidebar(self):
        staticpage = StaticPage.objects.get(title='Test page')
        url = reverse('manage:staticpage_edit', kwargs={'id': staticpage.id})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_fail = self.client.post(url, {
            'url': 'sidebar_bottom_main',
            'title': 'New test page',
            'content': '<p>New content</p>',
            'privacy': Event.PRIVACY_CONTRIBUTORS,
            'headers': '',
        })
        eq_(response_fail.status_code, 200)

        response_ok = self.client.post(url, {
            'url': 'sidebar_bottom_main',
            'title': 'New test page',
            'content': '<p>New content</p>',
            'privacy': Event.PRIVACY_PUBLIC,
            'headers': '',
        })
        self.assertRedirects(response_ok, reverse('manage:staticpages'))
        staticpage = StaticPage.objects.get(id=staticpage.id)
        eq_(staticpage.content, '<p>New content</p>')
        eq_('Sidebar (bottom) Main', staticpage.title)

    def test_staticpage_with_url_that_clashes(self):
        event = Event.objects.get(slug='test-event')
        StaticPage.objects.create(
            url='/' + event.slug,
            title='Some Page',
        )
        response = self.client.get(reverse('manage:staticpages'))
        eq_(response.status_code, 200)
        # there should now be a link to event it clashes with
        ok_('/pages/%s' % event.slug in response.content)
        event_url = reverse('main:event', args=(event.slug,))
        ok_(event_url in response.content)
