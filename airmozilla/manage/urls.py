from django.conf.urls.defaults import patterns, url

from . import views


urlpatterns = patterns('',
    url(r'^/?$', views.home, name='home'),
    url(r'^users/(?P<id>\d+)/$', views.user_edit, name='user_edit'),
    url(r'^users/', views.users, name='users'),
    url(r'^groups/(?P<id>\d+)/$', views.group_edit, name='group_edit'),
    url(r'^groups/new/$', views.group_new, name='group_new'),
    url(r'^groups/$', views.groups, name='groups'),
    url(r'^events/request/$', views.event_request, name='event_request'),
    url(r'^events/$', views.event_edit, name='event_edit'),
    url(r'^tag-autocomplete/$', views.tag_autocomplete,
                                name='tag_autocomplete'),
    url(r'^participant-autocomplete/$', views.participant_autocomplete,
                                        name='participant_autocomplete'),
    url(r'^participants/new/$', views.participant_new, name='participant_new'),
    url(r'^participants/(?P<id>\d+)/$', views.participant_edit,
                                       name='participant_edit'),
    url(r'^participants/$', views.participants, name='participants'),
    url(r'^categories/$', views.categories, name='categories'),
)
