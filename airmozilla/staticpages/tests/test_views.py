from nose.tools import ok_, eq_

from django.contrib.auth.models import AnonymousUser, User
from django.core.urlresolvers import reverse

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.main.models import Event, UserProfile
from airmozilla.staticpages.models import StaticPage
from airmozilla.staticpages.views import can_view_staticpage


class TestStaticPages(DjangoTestCase):

    def test_can_view_staticpage(self):
        from airmozilla.main.views import is_contributor
        anon = AnonymousUser()
        assert not is_contributor(anon)
        leonard = User.objects.create(
            username='leonard'
        )
        UserProfile.objects.create(
            user=leonard,
            contributor=True
        )
        assert is_contributor(leonard)
        peter = User.objects.create(
            username='peterbe'
        )
        assert not is_contributor(peter)

        page1 = StaticPage.objects.create(
            title="Title 1",
        )
        ok_(can_view_staticpage(page1, anon))
        ok_(can_view_staticpage(page1, leonard))
        ok_(can_view_staticpage(page1, peter))

        page2 = StaticPage.objects.create(
            title="Title 2",
            privacy=Event.PRIVACY_CONTRIBUTORS,
        )
        ok_(not can_view_staticpage(page2, anon))
        ok_(can_view_staticpage(page2, leonard))
        ok_(can_view_staticpage(page2, peter))

        page3 = StaticPage.objects.create(
            title="Title 3",
            privacy=Event.PRIVACY_COMPANY,
        )
        ok_(not can_view_staticpage(page3, anon))
        ok_(not can_view_staticpage(page3, leonard))
        ok_(can_view_staticpage(page3, peter))

    def test_staticpage(self):
        url = reverse('staticpages:staticpage', kwargs={
            'url': 'myurl'
        })
        response = self.client.get(url)
        eq_(response.status_code, 404)

        page = StaticPage.objects.create(
            title='My Title',
            url='/myurl'
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(page.title in response.content)

    def test_staticpage_not_allowed(self):
        url = reverse('staticpages:staticpage', kwargs={
            'url': 'myurl'
        })
        response = self.client.get(url)
        eq_(response.status_code, 404)

        page = StaticPage.objects.create(
            title='My Private Title',
            url='/myurl',
            content='Bla bla bla',
            privacy=Event.PRIVACY_COMPANY
        )
        response = self.client.get(url)
        eq_(response.status_code, 403)
        # because it's mentioned in the error message
        ok_(page.title in response.content)
        # the meat you're definitely not allowed to see
        ok_(page.content not in response.content)

        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_(page.title in response.content)
        ok_(page.content in response.content)

    def test_cors_header(self):
        StaticPage.objects.create(
            title='My Private Title',
            url='/myurl',
            content='Bla bla bla',
            headers={
                'access-control-allow-origin': '*'
            }
        )
        url = reverse('staticpages:staticpage', kwargs={
            'url': 'myurl'
        })
        response = self.client.get(url)
        eq_(response['Access-Control-Allow-Origin'], '*')

    def test_allow_querystring_variables(self):
        page = StaticPage.objects.create(
            title='My Private {{world}}',
            url='/myurl',
            content='Hello {{ world }}!',
        )
        url = reverse('staticpages:staticpage', kwargs={
            'url': 'myurl'
        })
        response = self.client.get(url)
        ok_('My Private {{world}}' in response.content)
        ok_('Hello {{ world }}!' in response.content)

        page.allow_querystring_variables = True
        page.save()
        response = self.client.get(url)
        ok_('My Private ' in response.content)
        ok_('Hello !' in response.content)

        response = self.client.get(url, {'world': 'WORLD'})
        ok_('My Private WORLD' in response.content)
        ok_('Hello WORLD!' in response.content)

        # But anything to do with request is not allowed because that's
        # where 'request.user' is
        page.content = "User is: {{ request.user }}"
        page.save()
        response = self.client.get(url, {'request.user': 'Devil'})
        ok_('User is: AnonymousUser' in response.content)

    def test_blank_template(self):
        StaticPage.objects.create(
            title='My Private Title',
            url='/myurl',
            content='Bla bla bla',
            template_name='staticpages/blank.html'
        )
        url = reverse('staticpages:staticpage', kwargs={
            'url': 'myurl'
        })
        response = self.client.get(url)
        eq_(response.status_code, 200)
        eq_(response.content, 'Bla bla bla')

    def test_nosidebar_template(self):
        page = StaticPage.objects.create(
            title='My Private Title',
            url='/myurl',
            content='Bla bla bla',
        )
        url = reverse('staticpages:staticpage', kwargs={
            'url': 'myurl'
        })
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('id="content-sub"' in response.content)

        page.template_name = 'staticpages/nosidebar.html'
        page.save()

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('id="content-sub"' not in response.content)
