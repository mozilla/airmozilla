from django.conf.urls.defaults import *
from django.views.generic.base import RedirectView

from . import views


urlpatterns = patterns('',
    url(r'^$', views.home, name='home'),
    url(r'^page/1/$', RedirectView.as_view(url='/'), name='first_page'),
    url(r'^page/(?P<page>\d+)/$', views.home, name='home'),
    url(r'^presenter/(?P<slug>[-\w]+)/$', views.participant, 
                                          name='participant'),
    url(r'^login/$', views.page, name='login',
        kwargs={'template': 'main/login.html'}),
    url(r'^login-failure/$', views.page, name='login_failure',
        kwargs={'template': 'main/login_failure.html'}),
    url(r'^about/$', views.page, name='about',
        kwargs={'template': 'main/about.html'}),
    url(r'^(?P<slug>[-\w]+)/$', views.event, name='event'),
)
