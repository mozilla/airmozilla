from django.conf import settings
from django.conf.urls import patterns, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

import djcelery

from airmozilla.base.monkeypatches import patch


patch()


handler500 = 'airmozilla.base.views.handler500'


urlpatterns = patterns(
    '',
    (r'^(?P<path>contribute\.json)$', 'django.views.static.serve',
     {'document_root': settings.ROOT}),
    (r'^manage/', include('airmozilla.manage.urls', namespace='manage')),
    (r'^requests/', include('airmozilla.suggest.urls', namespace='suggest')),
    (r'^search/', include('airmozilla.search.urls', namespace='search')),
    (r'^comments/', include('airmozilla.comments.urls', namespace='comments')),
    (r'^starred/', include('airmozilla.starred.urls', namespace='starred')),
    (r'^surveys/', include('airmozilla.surveys.urls', namespace='surveys')),
    (r'^uploads/', include('airmozilla.uploads.urls', namespace='uploads')),
    (r'^roku/', include('airmozilla.roku.urls', namespace='roku')),
    (r'^popcorn/', include('airmozilla.popcorn.urls', namespace='popcorn')),
    (r'^new/', include('airmozilla.new.urls', namespace='new')),
    ('^(?P<path>favicon\.ico)$', 'django.views.static.serve',
     {'document_root': settings.ROOT + '/airmozilla/base/static/img'}),
    (r'', include('django_browserid.urls')),
    (r'', include('airmozilla.main.urls', namespace='main')),
    ('^pages/', include('airmozilla.staticpages.urls',
     namespace='staticpages')),
)

# In DEBUG mode, serve media files through Django.
if settings.DEBUG:  # pragma: no cover
    # Remove leading and trailing slashes so the regex matches.
    media_url = settings.MEDIA_URL.lstrip('/').rstrip('/')
    urlpatterns += patterns(
        '',
        (r'^%s/(?P<path>.*)$' % media_url, 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT
        }),
    )
    urlpatterns += staticfiles_urlpatterns()


djcelery.setup_loader()
