from nose.tools import ok_, eq_
from funfactory.urlresolvers import reverse

from django.contrib.auth.models import AnonymousUser, User

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.main.models import Event, UserProfile
from airmozilla.staticpages.models import StaticPage
from airmozilla.staticpages.views import can_view_staticpage


class TestStaticPages(DjangoTestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']

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
