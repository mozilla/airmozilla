import json

from nose.tools import eq_, ok_

from django.test.utils import override_settings
from django.core.urlresolvers import reverse

from airmozilla.main.models import (
    URLTransform,
    URLMatch

)
from .base import ManageTestCase


class TestURLTransforms(ManageTestCase):

    @override_settings(URL_TRANSFORM_PASSWORDS={'foo': 'secret'})
    def test_url_transforms(self):
        url = reverse('manage:url_transforms')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        def quote(x):
            return x.replace("'", '&#39;')

        ok_(quote("{{ password('foo') }}") in response.content)

        # now with some matchers in there
        match = URLMatch.objects.create(
            name="Secure Things",
            string='secure'
        )
        URLTransform.objects.create(
            match=match,
            find='^secure',
            replace_with='insecure'
        )
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('Secure Things' in response.content)

    def test_url_match_new(self):
        url = reverse('manage:url_match_new')
        response = self.client.get(url)
        eq_(response.status_code, 200)

        response = self.client.post(url, {
            'name': 'Secure Things',
            'string': '^secure$'
        })
        self.assertRedirects(response, reverse('manage:url_transforms'))
        ok_(URLMatch.objects.get(string='^secure$'))

    def test_url_match_remove(self):
        match = URLMatch.objects.create(
            name="Secure Things",
            string='secure'
        )
        URLTransform.objects.create(
            match=match,
            find='^secure',
            replace_with='insecure'
        )
        eq_(URLMatch.objects.all().count(), 1)
        eq_(URLTransform.objects.all().count(), 1)

        url = reverse('manage:url_match_remove', args=(match.pk,))
        response = self.client.post(url)
        self.assertRedirects(response, reverse('manage:url_transforms'))

        eq_(URLMatch.objects.all().count(), 0)
        eq_(URLTransform.objects.all().count(), 0)

    def test_url_match_run(self):
        match = URLMatch.objects.create(
            name="Secure Things",
            string='secure'
        )
        URLTransform.objects.create(
            match=match,
            find='secure',
            replace_with='insecure'
        )
        url = reverse('manage:url_match_run')
        response = self.client.get(url, {
            'url': 'http://www.secure.com'
        })
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        ok_(not data['error'])
        eq_(data['result'], 'http://www.insecure.com')

    def test_url_tranform_add(self):
        match = URLMatch.objects.create(
            name="Secure Things",
            string='secure'
        )
        url = reverse('manage:url_transform_add', args=(match.pk,))
        response = self.client.post(url, {
            'find': 'secure',
            'replace_with': 'insecure'
        })
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        ok_(data['transform']['id'])

        ok_(
            URLTransform.objects.get(
                match=match,
                find='secure',
                replace_with='insecure'
            )
        )

    def test_url_tranform_edit(self):
        match = URLMatch.objects.create(
            name="Secure Things",
            string='secure'
        )
        transform = URLTransform.objects.create(
            match=match,
            find='secure',
            replace_with='insecure'
        )
        url = reverse('manage:url_transform_edit',
                      args=(match.pk, transform.pk))
        response = self.client.post(url, {
            'find': 'insecure',
            'replace_with': 'secure'
        })
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data, True)

        ok_(
            URLTransform.objects.get(
                match=match,
                find='insecure',
                replace_with='secure'
            )
        )

    def test_url_tranform_remove(self):
        match = URLMatch.objects.create(
            name="Secure Things",
            string='secure'
        )
        transform = URLTransform.objects.create(
            match=match,
            find='secure',
            replace_with='insecure'
        )
        url = reverse('manage:url_transform_remove',
                      args=(match.pk, transform.pk))
        response = self.client.post(url)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data, True)
        eq_(URLTransform.objects.all().count(), 0)
