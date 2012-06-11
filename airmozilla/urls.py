from django.conf import settings
from django.conf.urls.defaults import patterns, include

from funfactory.monkeypatches import patch
patch()

urlpatterns = patterns('',
    (r'', include('airmozilla.main.urls')),
    (r'', include('airmozilla.auth.urls')),
    (r'', include('airmozilla.manage.urls')),
)

## In DEBUG mode, serve media files through Django.
if settings.DEBUG:
    # Remove leading and trailing slashes so the regex matches.
    media_url = settings.MEDIA_URL.lstrip('/').rstrip('/')
    urlpatterns += patterns('',
        (r'^%s/(?P<path>.*)$' % media_url, 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT}),
    )
