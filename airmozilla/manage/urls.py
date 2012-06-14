from django.conf.urls.defaults import patterns, url

from . import views


urlpatterns = patterns('',
    url(r'^manage/?$', views.home, name='manage.home'),
    url(r'^manage/users/(?P<id>\d+)$', views.user_edit,
                             name='manage.user_edit'),
    url(r'^manage/users', views.users, name='manage.users'),
    url(r'^manage/groups/(?P<id>\d+)$', views.group_edit,
                             name='manage.group_edit'),
    url(r'^manage/groups/new$', views.group_new, name='manage.group_new'),
    url(r'^manage/groups', views.groups, name='manage.groups'),
    url(r'^manage/events/request', views.event_request,
                                   name='manage.event_request'),
    url(r'^manage/events', views.event_edit, name='manage.event_edit'),
    url(r'^manage/tag_autocomplete', views.tag_autocomplete,
                                     name='manage.tag_autocomplete'),
    url(r'^manage/participants', views.participant_edit,
                                 name='manage.participant_edit'),
)
