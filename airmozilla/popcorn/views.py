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
from django.db.models import Q
from django.conf import settings

from airmozilla.main.templatetags.jinja_helpers import thumbnail
from airmozilla.main.models import Event, VidlySubmission
from airmozilla.main.views.pages import EventView
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
            status=PopcornEdit.STATUS_SUCCESS,
            is_active=True).order_by('-created')[:1]:
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

    # Check to see if there is already an edit waiting to be processed
    for p_edit in PopcornEdit.objects.filter(
            event__slug=slug,
            is_active=True).order_by('-created')[:1]:
        if p_edit.status != PopcornEdit.STATUS_SUCCESS:
            msg = 'Already processing edit. Please try again soon.'
            return http.HttpResponseForbidden(msg)

    edit = PopcornEdit.objects.create(
        event=event,
        status=PopcornEdit.STATUS_PENDING,
        data=data,
        user=request.user,
    )

    return {
        'id': edit.id,
    }


@require_POST
@json_view
@login_required
@transaction.atomic
def revert(request, slug):
    event = get_object_or_404(Event, slug=slug)
    tag = request.POST.get('tag', '').strip()
    if not tag:
        return http.HttpResponseBadRequest("No 'tag'")

    vidly_submission = VidlySubmission.objects.get(tag=tag, event=event)

    migrate_submission(vidly_submission)
    # reload the event
    event = Event.objects.get(id=event.id)
    assert event.template_environment['tag'] == tag, "migration failed"

    edits = PopcornEdit.objects.filter(
        event=event
    ).order_by('-created')
    for edit in edits:
        if edit.upload.url != vidly_submission.url:
            edit.is_active = False
            edit.save()
        else:
            break

    return redirect('popcorn:edit_status', event.slug)


@login_required
def edit_status(request, slug):
    event = get_object_or_404(Event, slug=slug)

    edits = PopcornEdit.objects.filter(
        event=event,
        status__in=[
            PopcornEdit.STATUS_PENDING,
            PopcornEdit.STATUS_PROCESSING,
            PopcornEdit.STATUS_SUCCESS
        ],
        is_active=True,
    ).order_by('-created')

    first_submission, = (
        VidlySubmission.objects
        .filter(event=event, finished__isnull=False)
        .order_by('submission_time')
    )[:1]

    any_revertable_edits = False
    for edit in edits:
        if edit.status == PopcornEdit.STATUS_SUCCESS:

            submission = VidlySubmission.objects.get(
                event=event,
                url=edit.upload.url,
            )
            edit._tag = submission.tag
            edit._tag_finished = submission.finished
            if submission.finished:
                any_revertable_edits = True

    is_processing = is_waiting = is_transcoding = False
    if edits:
        status = edits[0].status
        if status == PopcornEdit.STATUS_PENDING:
            is_waiting = True
        elif status == PopcornEdit.STATUS_PROCESSING:
            is_processing = True
        elif status == PopcornEdit.STATUS_SUCCESS:
            # but has the vidlysubmission finished?
            submission = VidlySubmission.objects.get(
                event=event,
                url=edit.upload.url
            )
            if not submission.finished:
                is_transcoding = True

    context = {
        'PopcornEdit': PopcornEdit,
        'edits': edits,
        'event': event,
        'VidlySubmission': VidlySubmission,
        'first_submission': first_submission,
        'is_processing': is_processing,
        'is_waiting': is_waiting,
        'is_transcoding': is_transcoding,
        'any_revertable_edits': any_revertable_edits,
    }

    return render(request, 'popcorn/status.html', context)


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

        edit = None
        for p_edit in PopcornEdit.objects.filter(
                event=event,
                status=PopcornEdit.STATUS_SUCCESS,
                is_active=True).order_by('-created')[:1]:
            edit = p_edit

        pending_or_processing = (
            PopcornEdit.objects
            .filter(event=event, is_active=True)
            .filter(
                Q(status=PopcornEdit.STATUS_PENDING) |
                Q(status=PopcornEdit.STATUS_PROCESSING)
            )
            .exists()
        )
        if pending_or_processing:
            return redirect('popcorn:edit_status', event.slug)

        context = {
            'event': event,
            'edit': edit,
            'PopcornEdit': PopcornEdit,
            'slug': slug,
            'POPCORN_EDITOR_CDN_URL': settings.POPCORN_EDITOR_CDN_URL,
        }

        return render(request, self.template_name, context)
