from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns(
    '',
    url(r'^$', views.home, name='home'),
    url(r'^saved/$', views.savedsearches, name='savedsearches'),
    url(r'^saved/new/$', views.new_savedsearch, name='new_savedsearch'),
    url(r'^saved/data/$', views.savedsearches_data, name='savedsearches_data'),
    url(
        r'^saved/(?P<id>\d+)/delete/$',
        views.delete_savedsearch,
        name='delete_savedsearch'
    ),
    url(r'^saved/(?P<id>\d+)/$', views.savedsearch, name='savedsearch'),
    url(r'^save/$', views.savesearch, name='savesearch'),

)
