"""
To use this, add::

    MIDDLEWARE_CLASSES += ('airmozilla.base.middleware.JsonAsHTML',)

to your settings and for any AJAX request, you can open it
separately and add `&_debug=true` to the URL.
"""

from urllib import quote

from django.conf import settings


class JsonAsHTML(object):  # pragma: no cover
    '''
    View a JSON response in your browser as HTML
    Useful for viewing stats using Django Debug Toolbar

    This middleware should be place AFTER Django Debug Toolbar middleware
    '''

    def process_response(self, request, response):

        # not for production or production like environment
        if not settings.DEBUG:
            return response

        # do nothing for actual ajax requests
        if request.is_ajax() or not request.GET.get('_debug'):
            return response

        # only do something if this is a json response
        if response['Content-Type'].lower().startswith('application/json'):
            title = (
                'JSON as HTML Middleware for: %s' %
                quote(request.get_full_path())
            )
            content = response.content
            content = content.replace('<', '&lt;').replace('>', '&gt;')
            response.content = (
                '<!doctype html>\n<html><head><title>%s</title>'
                '<meta content="text/html; charset=UTF-8" '
                'http-equiv="Content-Type">'
                '</head>\n<body>\n%s\n</body></html>'
                % (title, content)
            )
            response['Content-Type'] = 'text/html'

        return response
