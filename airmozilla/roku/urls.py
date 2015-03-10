from django.conf.urls import patterns, url

from . import views


urlpatterns = patterns(
    '',
    url(r'categories.xml$',
        views.categories_feed,
        name='categories_feed'),
    url(r'event/(?P<id>\d+).xml$',
        views.event_feed,
        name='event_feed'),
    url(r'channel/trending.xml$',
        views.trending_feed,
        name='trending_feed'),
    url(r'channel/(?P<slug>[-\w]+).xml$',
        views.channel_feed,
        name='channel_feed'),
)
