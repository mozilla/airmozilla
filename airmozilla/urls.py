from django.conf import settings
from django.conf.urls.defaults import patterns, include

from .main import urls

from funfactory.monkeypatches import patch
patch()

urlpatterns = patterns('',
    (r'', include(urls)),
)

## In DEBUG mode, serve media files through Django.
if settings.DEBUG:
    # Remove leading and trailing slashes so the regex matches.
    media_url = settings.MEDIA_URL.lstrip('/').rstrip('/')
    urlpatterns += patterns('',
        (r'^%s/(?P<path>.*)$' % media_url, 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT}),
    )
