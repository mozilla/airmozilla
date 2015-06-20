from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns(
    '',
    url(r'^meta/$',
        views.event_meta_data,
        name='event_meta_data'),
)
