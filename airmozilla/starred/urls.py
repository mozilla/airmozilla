from django.views.generic.base import RedirectView
from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns(
    '',
    url(r'^page/1/$', RedirectView.as_view(url='/starred/', permanent=False),
        name='first_starred_page'),
    url(r'^page/(?P<page>\d+)/$', views.home, name='home'),
    url(r'^$', views.home, name='home'),
    url(r'^sync/$', views.sync_starred_events, name='sync'),
)
