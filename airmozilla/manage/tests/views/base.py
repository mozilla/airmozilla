from nose.tools import ok_

from django.test import TestCase
from django.contrib.auth.models import User

from funfactory.urlresolvers import reverse


class ManageTestCase(TestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']

    def shortDescription(self):
        # Stop nose using the test docstring and instead the test method name.
        pass

    def setUp(self):
        self.user = User.objects.create_superuser('fake', 'fake@f.com', 'fake')
        assert self.client.login(username='fake', password='fake')

    def _delete_test(self, obj, remove_view, redirect_view):
        """Common test for deleting an object in the management interface,
           checking that it was deleted properly, and ensuring that an improper
           delete request does not remove the object."""
        model = obj.__class__
        url = reverse(remove_view, kwargs={'id': obj.id})
        self.client.get(url)
        obj = model.objects.get(id=obj.id)
        ok_(obj)  # the template wasn't deleted because we didn't use POST
        response_ok = self.client.post(url)
        self.assertRedirects(response_ok, reverse(redirect_view))
        obj = model.objects.filter(id=obj.id).exists()
        ok_(not obj)
