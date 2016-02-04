from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns(
    '',
    url(r'^$', views.start, name='start'),
    url(r'^autocomplete-emails/', views.autocomplete_emails,
        name='autocomplete_emails'),
    url(r'^(?P<id>\d+)/title/$', views.title, name='title'),
    url(r'^(?P<id>\d+)/description/$', views.description, name='description'),
    url(r'^(?P<id>\d+)/details/$', views.details, name='details'),
    url(r'^(?P<id>\d+)/discussion/$', views.discussion, name='discussion'),
    url(r'^(?P<id>\d+)/image/$', views.placeholder, name='placeholder'),
    url(r'^(?P<id>\d+)/summary/$', views.summary, name='summary'),
    url(r'^(?P<id>\d+)/delete/$', views.delete, name='delete'),
)
