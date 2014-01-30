from django.test import TestCase
from django.conf import settings
from django.test.client import RequestFactory

from psycopg2 import OperationalError
from nose.tools import eq_, ok_


class ViewsPages(TestCase):

    def _get_handler500(self):
        root_urlconf = __import__(settings.ROOT_URLCONF,
                                  globals(), locals(), ['urls'], -1)
        # ...so that we can access the 'handler500' defined in there
        par, end = root_urlconf.handler500.rsplit('.', 1)
        # ...which is an importable reference to the real handler500 function
        views = __import__(par, globals(), locals(), [end], -1)
        # ...and finally we the handler500 function at hand
        return getattr(views, end)

    def test_500_page(self):
        handler500 = self._get_handler500()

        # to make a mock call to the django view functions you need a request
        fake_request = RequestFactory().request(**{'wsgi.input': None})

        # the reason for first causing an exception to be raised is because
        # the handler500 function is only called by django when an exception
        # has been raised which means sys.exc_info() is something.
        try:
            raise NameError("sloppy code!")
        except NameError:
            # do this inside a frame that has a sys.exc_info()
            response = handler500(fake_request)
            eq_(response.status_code, 500)
            ok_('Server Error' in response.content)
            ok_('NameError' not in response.content)

    def test_503_page(self):
        handler500 = self._get_handler500()

        # to make a mock call to the django view functions you need a request
        fake_request = RequestFactory().request(**{'wsgi.input': None})

        # the reason for first causing an exception to be raised is because
        # the handler500 function is only called by django when an exception
        # has been raised which means sys.exc_info() is something.
        try:
            raise OperationalError("unable to connect!")
        except OperationalError:
            # do this inside a frame that has a sys.exc_info()
            response = handler500(fake_request)
            eq_(response.status_code, 503)
            ok_('Temporarily Unavailable' in response.content)
