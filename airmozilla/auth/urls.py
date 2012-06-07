from django.conf.urls.defaults import patterns, url, include
from . import views

urlpatterns = patterns('',
    url(r'^browserid/mozilla', views.mozilla_browserid_verify, 
        name='auth.mozilla_browserid_verify'),
    url(r'^browserid/', include('django_browserid.urls')),
    url(r'^login_fail/', views.login_failure, name='auth.login_failure'),
    url(r'^logout/?$', 'django.contrib.auth.views.logout', {'next_page': '/'},
            name='auth.logout'),
)
