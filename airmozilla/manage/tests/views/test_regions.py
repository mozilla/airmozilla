from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse

from airmozilla.main.models import (
    Region,
)
from .base import ManageTestCase


class TestRegions(ManageTestCase):
    def setUp(self):
        super(TestRegions, self).setUp()
        Region.objects.create(name='South America')

    def test_regions(self):
        """Region management pages return successfully."""
        response = self.client.get(reverse('manage:regions'))
        eq_(response.status_code, 200)

        Region.objects.create(name='New Region')
        response = self.client.get(reverse('manage:regions'))
        eq_(response.status_code, 200)
        ok_('New Region' in response.content)

    def test_region_new(self):
        """Adding new region works correctly."""
        url = reverse('manage:region_new')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        response_ok = self.client.post(url, {
            'name': 'testing',
        })
        self.assertRedirects(response_ok, reverse('manage:regions'))

        response_fail = self.client.post(url)
        eq_(response_fail.status_code, 200)
        ok_('This field is required' in response_fail.content)

    def test_region_remove(self):
        """Removing a region works correctly and leaves associated locations
         with null regions."""
        region = Region.objects.create(
            name="Something"
        )
        self._delete_test(
            region,
            'manage:region_remove',
            'manage:regions'
        )
        assert not Region.objects.filter(name="Something")

    def test_region_edit(self):
        """Test region editor"""
        region = Region.objects.get(name='South America')
        url = reverse('manage:region_edit', kwargs={'id': region.id})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('South America' in response.content)

        response_ok = self.client.post(url, {
            'name': 'North America',
        })
        self.assertRedirects(response_ok, reverse('manage:regions'))
        ok_(Region.objects.get(name='North America'))

    def test_regions_inactive(self):
        Region.objects.create(name='New Region', is_active=False)
        response = self.client.get(reverse('manage:regions'))
        eq_(response.status_code, 200)
        ok_("Inactive region" in response.content)
