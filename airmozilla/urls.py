from django.conf import settings
from django.conf.urls.defaults import patterns, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from funfactory.monkeypatches import patch
patch()


handler500 = 'airmozilla.base.views.handler500'


urlpatterns = patterns(
    '',
    (r'^manage/', include('airmozilla.manage.urls', namespace='manage')),
    (r'^suggest/', include('airmozilla.suggest.urls', namespace='suggest')),
    ('^(?P<path>favicon\.ico)$', 'django.views.static.serve',
     {'document_root': settings.ROOT + '/airmozilla/base/static/img'}),
    (r'', include('airmozilla.auth.urls', namespace='auth')),
    (r'', include('airmozilla.main.urls', namespace='main')),
    ('^pages/', include('django.contrib.flatpages.urls')),
)

## In DEBUG mode, serve media files through Django.
if settings.DEBUG:
    # Remove leading and trailing slashes so the regex matches.
    media_url = settings.MEDIA_URL.lstrip('/').rstrip('/')
    urlpatterns += patterns(
        '',
        (r'^%s/(?P<path>.*)$' % media_url, 'django.views.static.serve',
        {'document_root': settings.MEDIA_ROOT}),
    )
    urlpatterns += staticfiles_urlpatterns()
