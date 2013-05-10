from nose.tools import eq_, ok_

from django.test import TestCase
from django.conf import settings

from airmozilla.main.models import URLMatch, URLTransform
from airmozilla.manage import url_transformer


class URLTransformerTestCase(TestCase):

    def setUp(self):
        super(URLTransformerTestCase, self).setUp()
        settings.URL_TRANSFORM_PASSWORDS = {
            'foo': 'bar',
        }

    def test_run(self):
        url = 'http://www.com/test'
        result, error = url_transformer.run(url)
        ok_(not error)
        eq_(result, url)

        match1 = URLMatch.objects.create(
            name='Duff 1',
            string='test'
        )
        URLTransform.objects.create(
            match=match1,
            find='^test',
            replace_with="WON'T"
        )
        URLTransform.objects.create(
            match=match1,
            find='test$',
            replace_with='WORK'
        )

        match2 = URLMatch.objects.create(
            name='Secure',
            string='://'
        )
        URLTransform.objects.create(
            match=match2,
            find='://',
            replace_with="://foo:{{ password('foo') }}@"
        )

        result, error = url_transformer.run(url)
        ok_(not error)
        eq_(
            result,
            'http://foo:bar@www.com/WORK'
        )

        result, error = url_transformer.run(url, dry=True)
        ok_(not error)
        ok_(result.startswith('http://foo:'))
        ok_('bar' not in result)
