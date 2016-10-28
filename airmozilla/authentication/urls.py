from django.conf.urls import patterns, url
from airmozilla.authentication import views


urlpatterns = patterns(
    '',
    url('^callback/$', views.callback, name='callback'),
    url('^signin/$', views.signin, name='signin'),
    url('^signout/$', views.signout, name='signout'),
)
