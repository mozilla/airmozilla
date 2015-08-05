import json
from urlparse import urlparse
from xml.parsers.expat import ExpatError

from jsonview.decorators import json_view
import requests
import xmltodict

from django import http
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone

from airmozilla.main.helpers import thumbnail
from airmozilla.main.models import Event, VidlySubmission
from airmozilla.main.views import EventView
from airmozilla.manage.archiver import email_about_archiver_error
from airmozilla.manage import vidly
from airmozilla.popcorn.models import PopcornEdit


def add_cors_header(value):
    def decorator(f):
        def inner(*args, **kwargs):
            response = f(*args, **kwargs)
            response['Access-Control-Allow-Origin'] = value
            return response
        return inner
    return decorator


def get_video_url(event):
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

    # Remove cache buster params since filename must be consistent for videos
    purl = urlparse(response.headers['location'])
    location = r'{0}://{1}{2}'.format(purl.scheme, purl.hostname, purl.path)

    return location


def get_thumbnail(event):
    image = event.picture and event.picture.file or event.placeholder_img
    geometry = '160x90'
    crop = 'center'

    return thumbnail(image, geometry, crop=crop)


@add_cors_header('*')
@json_view
def event_meta_data(request):
    if not request.GET.get('slug'):
        return http.HttpResponseBadRequest('slug')
    event = get_object_or_404(Event, slug=request.GET['slug'])

    video_url = get_video_url(event)

    thumb = get_thumbnail(event)

    return {
        'title': event.title,
        'description': event.short_description or event.description,
        'preview_img': thumb.url,
        'video_url': video_url,
    }


@json_view
@login_required
def popcorn_data(request):
    slug = request.GET.get('slug')
    if not slug:
        return http.HttpResponseBadRequest('slug')
    event = get_object_or_404(Event, slug=slug)

    for edit in PopcornEdit.objects.filter(
            event__slug=slug,
            status=PopcornEdit.STATUS_SUCCESS).order_by('-created')[:1]:
        data = edit.data
        return {'data': edit.data}
    else:
        video_url = get_video_url(event)
        thumb = get_thumbnail(event)
        data = {
            'thumbnail': thumb.url,
            'url': video_url,
            'title': event.title,
            'duration': event.duration,
            'type': 'AirMozilla',
        }

        return {
            "metadata": data,
        }


@json_view
@login_required
@require_POST
@transaction.atomic
def save_edit(request):
    slug = request.POST.get('slug')
    if not slug:
        return http.HttpResponseBadRequest('slug')
    data = request.POST.get('data')
    if not data:
        return http.HttpResponseBadRequest('data')
    try:
        data = json.loads(data)
    except ValueError as exception:
        return http.HttpResponseBadRequest(exception)

    event = get_object_or_404(Event, slug=slug)

    edit = PopcornEdit.objects.create(
        event=event,
        status=PopcornEdit.STATUS_PENDING,
        data=data,
        user=request.user,
    )

    return {
        'id': edit.id,
    }


# Note that this view is publically available.
# That means we can't trust the content but we can take it as a hint.
@csrf_exempt
@require_POST
def vidly_webhook(request):
    if not request.POST.get('xml'):
        return http.HttpResponseBadRequest("no 'xml'")

    xml_string = request.POST['xml'].strip()
    try:
        struct = xmltodict.parse(xml_string)
    except ExpatError:
        return http.HttpResponseBadRequest("Bad 'xml'")

    try:
        task = struct['Response']['Result']['Task']
    except KeyError:
        # If it doesn't have a "Result" or "Task", it was just a notification
        # that the media was added.
        pass

    migrate_submission(
        get_object_or_404(
            VidlySubmission,
            url=task['SourceFile'],
            tag=task['MediaShortLink'],
        )
    )

    return http.HttpResponse('OK\n')


def migrate_submission(vidly_submission):
    shortlink = vidly_submission.tag
    results = vidly.query(shortlink)

    if results[shortlink]['Status'] == 'Finished':
        if not vidly_submission.finished:
            vidly_submission.finished = timezone.now()
            vidly_submission.save()

        event = vidly_submission.event
        event.template_environment['tag'] = shortlink
        event.save()

    elif results[shortlink]['Status'] == 'Error':
        if not vidly_submission.errored:
            vidly_submission.errored = timezone.now()
            vidly_submission.save()

            email_about_archiver_error(
                event=vidly_submission.event,
                tag=shortlink,
            )


class EditorView(EventView):
    template_name = 'popcorn/editor.html'

    def can_edit_event(self, event, request):
        # this might change in the future to only be
        # employees and vouched mozillians
        return request.user.is_active

    def cant_edit_event(self, event, user):
        return redirect('main:event', event.slug)

    def get(self, request, slug, form=None, conflict_errors=None):
        event = self.get_event(slug, request)
        if isinstance(event, http.HttpResponse):
            return event

        if not self.can_view_event(event, request):
            return self.cant_view_event(event, request)
        if not self.can_edit_event(event, request):
            return self.cant_edit_event(event, request)

        context = {
            'event': event,
            'slug': slug,
        }

        return render(request, self.template_name, context)
