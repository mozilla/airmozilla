from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns(
    '',
    url(r'^download/(?P<filename_hash>\w{12})/(?P<id>\d+)/'
        r'(?P<slug>[-\w]+).(?P<extension>\w+)$',
        views.download,
        name='download'),
)
