from django.conf.urls import patterns, url

from . import views

urlpatterns = patterns(
    '',
    url(r'^meta/$',
        views.event_meta_data,
        name='event_meta_data'),
    url(r'^edit/(?P<slug>[-\w]+)/$',
        views.EditorView.as_view(),
        name='render_editor'),
    url(r'^data/$',
        views.popcorn_data,
        name='popcorn_data'),
    url(r'^vidlywebhook/$',
        views.vidly_webhook,
        name='vidly_webhook'),
    url(r'^save/$',
        views.save_edit,
        name='save_edit'),
    url(r'^status/(?P<slug>[-\w]+)/$',
        views.edit_status,
        name='edit_status'),
    url(r'^status/(?P<slug>[-\w]+)/revert/$',
        views.revert,
        name='revert'),
)
