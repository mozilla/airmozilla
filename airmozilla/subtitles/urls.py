from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns(
    '',
    url(r'amara/callback/$',
        views.amara_callback,
        name='amara_callback'),
)
