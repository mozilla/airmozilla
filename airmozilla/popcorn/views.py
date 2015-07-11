import requests
from jsonview.decorators import json_view

from django import http
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from airmozilla.main.helpers import thumbnail
from airmozilla.main.models import Event, VidlySubmission
from airmozilla.main.views import EventView


def add_cors_header(value):
    def decorator(f):
        def inner(*args, **kwargs):
            response = f(*args, **kwargs)
            response['Access-Control-Allow-Origin'] = value
            return response
        return inner
    return decorator


@add_cors_header('*')
@json_view
def event_meta_data(request):
    slug = request.GET.get('slug')
    event = get_object_or_404(Event, slug=slug)

    image = event.picture and event.picture.file or event.placeholder_img
    geometry = '160x90'
    crop = 'center'

    thumb = thumbnail(image, geometry, crop=crop)

    if event.template and 'vid.ly' in event.template.name.lower():
        tag = event.template_environment['tag']

        video_format = 'webm'

        for submission in VidlySubmission.objects.filter(event=event, tag=tag):
            if submission.hd:
                video_format = 'hd_webm'

        video_url = 'https://vid.ly/{0}?content=video&format={1}'.format(
            tag, video_format
        )
    else:
        return http.HttpResponseBadRequest('Event is not a Vidly video')

    response = requests.head(video_url)

    assert response.status_code == 302, response.status_code

    return {
        'title': event.title,
        'description': event.short_description or event.description,
        'preview_img': thumb.url,
        'video_url': response.headers['location'],
    }


class EditorView(EventView):
    template_name = 'popcorn/editor.html'

    def can_edit_event(self, event, request):
        # this might change in the future to only be
        # employees and vouched mozillians
        return request.user.is_active

    def cant_edit_event(self, event, user):
        return redirect('main:event', event.slug)

    @staticmethod
    def event_to_dict(event):
        data = {
            'event_id': event.id,
            'title': event.title,
            'description': event.description,
            'short_description': event.short_description,
        }
        return data

    def get(self, request, slug, form=None, conflict_errors=None):
        event = self.get_event(slug, request)
        print event
        if isinstance(event, http.HttpResponse):
            return event

        if not self.can_view_event(event, request):
            return self.cant_view_event(event, request)
        if not self.can_edit_event(event, request):
            return self.cant_edit_event(event, request)

        context = {
            'event': event
        }

        return render(request, self.template_name, context)


@login_required
def render_editor(request):
    return render(request, 'popcorn/editor.html', {})
