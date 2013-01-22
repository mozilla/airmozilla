from django.conf.urls.defaults import patterns, url
from django.views.generic.base import RedirectView
from django.views.decorators.cache import cache_page

from . import views


urlpatterns = patterns(
    '',
    url(r'^$', views.home, name='home'),
    url(r'^channels/(?P<channel_slug>[-\w]+)/$', views.home,
        name='home_channels'),
    url(r'^page/1/$', RedirectView.as_view(url='/'), name='first_page'),
    url(r'^page/(?P<page>\d+)/$', views.home, name='home'),
    url(r'^channels/(?P<channel_slug>[-\w]+)/page/(?P<page>\d+)/$',
        views.home, name='home_channels'),
    url(r'^channels/$', views.channels, name='channels'),
    url(r'^presenter/(?P<slug>[-\w]+)/$', views.participant,
        name='participant'),
    url(r'^presenter-clear/(?P<clear_token>[-\w]+)/$', views.participant_clear,
        name='participant_clear'),
    url(r'^login/$', views.page, name='login',
        kwargs={'template': 'main/login.html'}),
    url(r'^login-failure/$', views.page, name='login_failure',
        kwargs={'template': 'main/login_failure.html'}),
    url(r'^about/$', views.page, name='about',
        kwargs={'template': 'main/about.html'}),
    url(r'^calendar/$', views.events_calendar, name='calendar'),
    url(r'^calendar/private/$', views.events_calendar,
        kwargs={'public': False}, name='private_calendar'),
    url(r'^feed/(public|private|both)?/?$',
        cache_page(views.EventsFeed(), 60 * 60),
        name='feed'),
    url(r'^feed/(?P<channel_slug>[-\w]+)/(public|private)?/?$',
        cache_page(views.EventsFeed(), 60 * 60),
        name='channel_feed'),
    url(r'^(?P<slug>[-\w]+)/$', views.event, name='event'),
)
