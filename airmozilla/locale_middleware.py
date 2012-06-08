"""
Custom middleware replaces funfactory.middleware.LocaleURLMiddleware
to disable URL redirects but keep tower activation.
"""

import tower

from funfactory import urlresolvers


class LocaleURLMiddleware(object):

    def process_request(self, request):
        prefixer = urlresolvers.Prefixer(request)
        tower.activate(prefixer.locale)
