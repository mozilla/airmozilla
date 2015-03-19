# Quite blatantly copied from django.contrib.flatpages.middleware

from django.http import Http404
from django.conf import settings

from .views import staticpage


class StaticPageFallbackMiddleware(object):

    def process_response(self, request, response):
        if response.status_code != 404:
            # No need to check for a page for non-404 responses.
            return response
        try:
            return staticpage(request, request.path_info)
        # Return the original response if any errors happened. Because this
        # is a middleware, we can't assume the errors will be caught elsewhere.
        except Http404:
            return response
        except:
            if settings.DEBUG:
                raise
            return response
