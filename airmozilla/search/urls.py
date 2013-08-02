from django.conf.urls.defaults import patterns, url

from . import views

urlpatterns = patterns(
    '',
    url(r'^$', views.home, name='home'),
)
