from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns(
    '',
    url(r'^$', views.home, name='home'),
    url(r'^save/(?P<id>\d+)/$', views.savedsearch, name='savedsearch'),
    url(r'^save/(?P<slug>[-\w]+)/$', views.savedsearch, name='savedsearch'),
    url(r'^save/$', views.savesearch, name='savesearch'),
)
