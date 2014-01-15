from django.conf.urls.defaults import patterns, url

from . import views

urlpatterns = patterns(
    '',
    url(r'^$', views.home, name='home'),
    url(r'^upload/$', views.upload, name='upload'),
    url(r'^save/$', views.save, name='save'),
    url(r'^sign/$', views.sign, name='sign'),
    url(r'^verify-size/$', views.verify_size,
        name='verify_size'),
)
