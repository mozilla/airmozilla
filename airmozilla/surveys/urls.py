from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns(
    '',
    url(r'load/(?P<id>\d+)/$',
        views.load,
        name='load'),
)
