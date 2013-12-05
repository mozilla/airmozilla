from django.conf.urls.defaults import patterns, url

from . import views

urlpatterns = patterns(
    '',
    url(r'user-name/$',
        views.user_name,
        name='user_name'),
    url(r'approve/(?P<identifier>\w{10})/(?P<id>\d+)/$',
        views.approve_immediately,
        name='approve_immediately'),
    url(r'remove/(?P<identifier>\w{10})/(?P<id>\d+)/$',
        views.remove_immediately,
        name='remove_immediately'),
    url(r'unsubscribed/(?P<id>\d+)/$',
        views.unsubscribed,
        name='unsubscribed'),
    url(r'unsubscribed/$',
        views.unsubscribed,
        name='unsubscribed_all'),
    url(r'unsubscribe/(?P<identifier>\w{10})/(?P<id>\d+)/$',
        views.unsubscribe,
        name='unsubscribe_discussion'),
    url(r'unsubscribe/(?P<identifier>\w{10})/$',
        views.unsubscribe,
        name='unsubscribe_all'),
    url(r'(?P<id>\d+)/latest/$',
        views.event_data_latest,
        name='event_data_latest'),
    url(r'(?P<id>\d+)/$',
        views.event_data,
        name='event_data'),
)
