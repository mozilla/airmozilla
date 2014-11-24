from django.conf.urls import patterns, url

from . import views


urlpatterns = patterns(
    '',
    url(r'^$',
        views.start,
        name='start'),
    url(r'^(?P<id>\d+)/details/$',
        views.details,
        name='details'),
    url(r'^(?P<id>\d+)/picture/$',
        views.placeholder,
        name='placeholder'),
    url(r'^(?P<id>\d+)/photobooth/$',
        views.photobooth,
        name='photobooth'),
    url(r'^(?P<id>\d+)/video/$',
        views.video,
        name='video'),
    url(r'^(?P<id>\d+)/summary/$',
        views.summary,
        name='summary'),
    url(r'^save/$',
        views.save,
        name='save'),
)
