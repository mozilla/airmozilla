import json

from nose.tools import eq_, ok_

from funfactory.urlresolvers import reverse

from airmozilla.main.models import Template
from .base import ManageTestCase


class TestTemplates(ManageTestCase):

    def test_templates(self):
        """Templates listing responds OK."""
        response = self.client.get(reverse('manage:templates'))
        eq_(response.status_code, 200)

    def test_template_new(self):
        """New template form responds OK and results in a new template."""
        url = reverse('manage:template_new')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_ok = self.client.post(url, {
            'name': 'happy template',
            'content': 'hello!'
        })
        self.assertRedirects(response_ok, reverse('manage:templates'))
        ok_(Template.objects.get(name='happy template'))
        response_fail = self.client.post(url)
        eq_(response_fail.status_code, 200)

    def test_template_edit(self):
        """Template editor response OK, results in changed data or fail."""
        template = Template.objects.get(name='test template')
        url = reverse('manage:template_edit', kwargs={'id': template.id})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_ok = self.client.post(url, {
            'name': 'new name',
            'content': 'new content'
        })
        self.assertRedirects(response_ok, reverse('manage:templates'))
        template = Template.objects.get(id=template.id)
        eq_(template.content, 'new content')
        response_fail = self.client.post(url, {
            'name': 'no content'
        })
        eq_(response_fail.status_code, 200)

    def test_template_edit_default_popcorn_template(self):
        """Editing a template and setting `default_popcorn_template` should
        un-set that for any others."""
        Template.objects.create(
            name='Template 1',
            content='Bla bla'
        )
        Template.objects.create(
            name='Template 2',
            content='Ble ble',
            default_popcorn_template=True
        )
        template = Template.objects.get(name='test template')
        url = reverse('manage:template_edit', kwargs={'id': template.id})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_ok = self.client.post(url, {
            'name': 'new name',
            'content': 'new content',
            'default_popcorn_template': True
        })
        # print response.content
        eq_(response_ok.status_code, 302)
        # reload
        template = Template.objects.get(pk=template.id)
        ok_(template.default_popcorn_template)
        self.assertRedirects(response_ok, reverse('manage:templates'))
        # only exactly one should have default_popcorn_template on
        eq_(Template.objects.filter(default_popcorn_template=True).count(), 1)

    def test_template_remove(self):
        template = Template.objects.get(name='test template')
        self._delete_test(template, 'manage:template_remove',
                          'manage:templates')

    def test_template_env_autofill(self):
        """The JSON autofiller responds correctly for the fixture template."""
        template = Template.objects.get(name='test template')
        response = self.client.get(reverse('manage:template_env_autofill'),
                                   {'template': template.id})
        eq_(response.status_code, 200)
        template_parsed = json.loads(response.content)
        ok_(template_parsed)
        eq_(template_parsed, {'variables': 'tv1=\ntv2='})

    def test_template_env_autofill_with_popcorn_url(self):
        template = Template.objects.get(name='test template')
        template.content = """
        <iframe src="{{ popcorn_url }}"></ifram>
        """
        template.save()
        response = self.client.get(reverse('manage:template_env_autofill'),
                                   {'template': template.id})
        eq_(response.status_code, 200)
        template_parsed = json.loads(response.content)
        eq_(template_parsed, {'variables': ''})
