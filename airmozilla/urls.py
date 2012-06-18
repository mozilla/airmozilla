from django.conf import settings
from django.conf.urls.defaults import patterns, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from funfactory.monkeypatches import patch
patch()

urlpatterns = patterns('',
    (r'', include('airmozilla.main.urls')),
    (r'', include('airmozilla.auth.urls')),
    (r'', include('airmozilla.manage.urls')),
)

## In DEBUG mode, serve media files through Django.
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
