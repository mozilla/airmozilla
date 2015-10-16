import json

from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse

from airmozilla.main.models import (
    Location,
    Region,
    Template,
    Event,
    LocationDefaultEnvironment
)
from .base import ManageTestCase


class TestLocations(ManageTestCase):
    def test_locations(self):
        """Location management pages return successfully."""
        response = self.client.get(reverse('manage:locations'))
        eq_(response.status_code, 200)

        location = Location.objects.create(name='SomeLocation')
        response = self.client.get(reverse('manage:locations'))
        eq_(response.status_code, 200)
        eq_(location.name, 'SomeLocation')

    def test_locations_regions(self):
        """Location management pages with regions return successfully."""
        response = self.client.get(reverse('manage:locations'))
        eq_(response.status_code, 200)

        location = Location.objects.create(name='SomeLocation')
        region = Region.objects.create(name='SomeRegion')
        location.regions.add(region)
        response = self.client.get(reverse('manage:locations'))
        eq_(response.status_code, 200)
        ok_('SomeLocation' in response.content)
        ok_('SomeRegion' in response.content)

    def test_location_new(self):
        """Adding new location works correctly."""
        url = reverse('manage:location_new')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_ok = self.client.post(url, {
            'name': 'testing',
            'timezone': 'US/Pacific'
        })
        self.assertRedirects(response_ok, reverse('manage:locations'))
        location = Location.objects.get(name='testing')
        eq_(location.timezone, 'US/Pacific')
        response_fail = self.client.post(url)
        eq_(response_fail.status_code, 200)

    def test_location_remove(self):
        """Removing a location works correctly and leaves associated events
         with null locations."""
        location = Location.objects.create(
            name="Something"
        )
        self._delete_test(
            location,
            'manage:location_remove',
            'manage:locations'
        )

        # but for the location in the fixture this is not allowed
        location = Location.objects.get(id=1)
        url = reverse('manage:location_remove', args=(location.id,))
        response = self.client.post(url)
        eq_(response.status_code, 400)

    def test_location_edit(self):
        """Test location editor; timezone switch works correctly."""
        url = reverse('manage:location_edit', kwargs={'id': 1})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_ok = self.client.post(url, {
            'name': 'eastern',
            'timezone': 'US/Eastern'
        })
        self.assertRedirects(response_ok, reverse('manage:locations'))
        location = Location.objects.get(id=1)
        eq_(location.timezone, 'US/Eastern')
        response_fail = self.client.post(url, {
            'name': 'eastern',
            'timezone': 'notatimezone'
        })
        eq_(response_fail.status_code, 200)

    def test_location_edit_default_environment(self):
        location = Location.objects.get(id=1)
        url = reverse('manage:location_edit', kwargs={'id': location.id})
        # suppose you try to submit a new LocationDefaultEnvironment
        template = Template.objects.create(name='My Template')
        response = self.client.post(url, {
            'default': 1,
            'privacy': Event.PRIVACY_PUBLIC,
            'template': template.pk
        })
        ok_('This field is required')
        eq_(response.status_code, 200)
        response = self.client.post(url, {
            'default': 1,
            'privacy': Event.PRIVACY_PUBLIC,
            'template': template.pk,
            'template_environment': 'foo=bar\nbaz=fuzz'
        })
        eq_(response.status_code, 302)

        default = LocationDefaultEnvironment.objects.get(location=location)
        eq_(default.privacy, Event.PRIVACY_PUBLIC)
        eq_(default.template, template)
        eq_(default.template_environment, {'foo': 'bar', 'baz': 'fuzz'})

        # you can't create another one with only
        # different template_environment
        response = self.client.post(url, {
            'default': 1,
            'privacy': Event.PRIVACY_PUBLIC,
            'template': template.pk,
            'template_environment': 'diff=erent'
        })
        eq_(response.status_code, 302)
        eq_(LocationDefaultEnvironment.objects.all().count(), 1)

        # and now delete it
        response = self.client.post(url, {
            'delete': default.pk,
        })
        eq_(response.status_code, 302)
        eq_(LocationDefaultEnvironment.objects.all().count(), 0)

    def test_location_timezone(self):
        """Test timezone-ajax autofill."""
        url = reverse('manage:location_timezone')
        response_fail = self.client.get(url)
        eq_(response_fail.status_code, 404)
        response_fail = self.client.get(url, {'location': ''})
        eq_(response_fail.status_code, 404)
        response_fail = self.client.get(url, {'location': '23323'})
        eq_(response_fail.status_code, 404)
        response_ok = self.client.get(url, {'location': '1'})
        eq_(response_ok.status_code, 200)
        data = json.loads(response_ok.content)
        ok_('timezone' in data)
        eq_(data['timezone'], 'US/Pacific')
