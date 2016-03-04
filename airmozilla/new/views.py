# -*- coding: utf-8 -*-

import json
import os
from cStringIO import StringIO
from xml.parsers.expat import ExpatError

import requests
import xmltodict
from PIL import Image
from slugify import slugify

from django import http
from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required
from django.utils.functional import wraps
from django.template.base import TemplateDoesNotExist
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.core.files import File
from django.core.files.temp import NamedTemporaryFile

from jsonview.decorators import json_view
from sorl.thumbnail import get_thumbnail

from airmozilla.manage import vidly
from airmozilla.base.utils import get_base_url, prepare_vidly_video_url
from airmozilla.main.models import (
    Event,
    VidlySubmission,
    Template,
    Picture,
    EventOldSlug,
    Channel,
    Approval,
    get_profile_safely,
    Tag,
)
from airmozilla.comments.models import Discussion
from airmozilla.uploads.models import Upload
from airmozilla.manage import videoinfo
from airmozilla.base.templatetags.jinja_helpers import show_duration
from airmozilla.base.utils import simplify_form_errors
from airmozilla.manage import sending
from airmozilla.base import youtube
from . import forms


def xhr_login_required(view_func):
    """similar to django.contrib.auth.decorators.login_required
    except instead of redirecting it returns a 403 message if not
    authenticated."""
    @wraps(view_func)
    def inner(request, *args, **kwargs):
        if not request.user.is_authenticated():
            return http.HttpResponse(
                json.dumps({'error': "You must be logged in"}),
                content_type='application/json',
                status=403
            )
        return view_func(request, *args, **kwargs)

    return inner


def must_be_your_event(f):
    @wraps(f)
    def inner(request, id, **kwargs):
        assert request.user.is_authenticated()
        event = get_object_or_404(Event, pk=id)
        if event.creator != request.user:
            return http.HttpResponseForbidden(
                "Not your event to meddle with"
            )
        return f(request, event, **kwargs)

    return inner


@login_required
def home(request):
    context = {
        'has_youtube_api_key': bool(settings.YOUTUBE_API_KEY),
    }
    request.show_sidebar = False
    return render(request, 'new/home.html', context)


@xhr_login_required
def partial_template(request, template_name):
    context = {}
    if template_name == 'details.html':
        context['form'] = forms.DetailsForm()
    template_path = os.path.join('new/partials', template_name)
    try:
        return render(request, template_path, context)
    except TemplateDoesNotExist:
        raise http.Http404(template_name)


@json_view
@xhr_login_required
@require_POST
@transaction.atomic
def save_upload(request):
    data = json.loads(request.body)
    form = forms.SaveForm(data)
    if not form.is_valid():
        return http.HttpResponseBadRequest(form.errors)

    url = form.cleaned_data['url']
    file_name = form.cleaned_data['file_name'] or os.path.basename(url)
    mime_type = form.cleaned_data['mime_type']
    size = form.cleaned_data['size']
    upload_time = form.cleaned_data['upload_time']
    duration = data.get('duration')

    new_upload = Upload.objects.create(
        user=request.user,
        url=url,
        size=size,
        file_name=file_name,
        mime_type=mime_type,
        upload_time=upload_time,
    )

    # now we can create the event to start with
    event = Event.objects.create(
        upload=new_upload,
        status=Event.STATUS_INITIATED,
        start_time=timezone.now(),
        privacy=Event.PRIVACY_PUBLIC,
        creator=request.user,
        duration=duration,
    )
    new_upload.event = event
    new_upload.save()

    return {'id': event.id}


@never_cache
@xhr_login_required
@transaction.atomic
@must_be_your_event
@json_view
def event_edit(request, event):
    if request.method == 'POST':
        if event.status != Event.STATUS_INITIATED:
            return http.HttpResponseBadRequest(
                "You can't edit events that are NOT in the state of initiated."
            )
        title_before = event.title
        form = forms.DetailsForm(json.loads(request.body), instance=event)
        if form.is_valid():
            form.save()
            if event.title != title_before:
                # Un-setting it will automatically pick a good slug.
                # But first we need to forget any EventOldSlug
                EventOldSlug.objects.filter(slug=event.slug).delete()
                event.slug = None
                event.save()
        else:
            return {'errors': simplify_form_errors(form.errors)}

    context = {
        'event': serialize_event(event),
    }
    return context


def serialize_event(event, extended=False):
    data = {
        'id': event.id,
        'title': event.title,
        'slug': event.slug,
        'description': event.description,
        'privacy': event.privacy,
        'privacy_display': event.get_privacy_display(),
        'status': event.status,
        'status_display': event.get_status_display(),
        'additional_links': event.additional_links,
        'duration': event.duration,
        'tags': [],
        'channels': {},
        'topics': {},
    }
    if extended:
        # When it's the extended version, we return a list of dicts
        # that contain the id, name, etc.
        data['channels'] = []
        data['topics'] = []

    if event.slug:
        data['url'] = reverse('main:event', args=(event.slug,))
    for tag in event.tags.all():
        data['tags'].append(tag.name)  # good enough?
    # lastly, make it a string
    data['tags'] = ', '.join(sorted(data['tags']))

    for channel in event.channels.all():
        if extended:
            data['channels'].append({
                'id': channel.id,
                'name': channel.name,
                'url': reverse('main:home_channels', args=(channel.slug,)),
            })
        else:
            data['channels'][channel.id] = True

    for topic in event.topics.all():
        if extended:
            data['topics'].append({
                'id': topic.id,
                'topic': topic.topic,
            })
        else:
            data['topics'][topic.id] = True

    if extended:
        # get a list of all the groups that need to approve it
        data['approvals'] = []
        for approval in Approval.objects.filter(event=event, approved=False):
            data['approvals'].append({
                'group_name': approval.group.name,
            })

    if event.placeholder_img or event.picture:
        geometry = '160x90'
        crop = 'center'
        if event.picture:
            thumb = get_thumbnail(
                event.picture.file, geometry, crop=crop
            )
        else:
            thumb = get_thumbnail(
                event.placeholder_img, geometry, crop=crop
            )
        data['picture'] = {
            'url': thumb.url,
            'width': thumb.width,
            'height': thumb.height,
        }
    if event.upload:
        data['upload'] = {
            'size': event.upload.size,
            'url': event.upload.url,
            'mime_type': event.upload.mime_type,
        }
    elif (
        'youtube' in event.template.name.lower() and
        event.template_environment.get('id')
    ):
        data['upload'] = None
        data['youtube_id'] = event.template_environment['id']

    return data


@require_POST
@login_required
@transaction.atomic
@must_be_your_event
@json_view
def event_archive(request, event):
    if event.status != Event.STATUS_INITIATED:
        return http.HttpResponseBadRequest(
            "You can't archive events that are NOT in the state of initiated."
        )

    submissions = VidlySubmission.objects.filter(
        event=event,
        url__startswith=event.upload.url
    )
    for vidly_submission in submissions.order_by('-submission_time'):
        break
    else:
        # we haven't sent it in for archive yet
        upload = event.upload
        base_url = get_base_url(request)
        webhook_url = base_url + reverse('new:vidly_media_webhook')

        video_url = prepare_vidly_video_url(upload.url)
        tag, error = vidly.add_media(
            video_url,
            hd=True,
            notify_url=webhook_url,
            # Note that we deliberately don't bother yet to set
            # token_protection here because we don't yet know if the
            # event is going to be private or not.
            # Also, it's much quicker to make screencaptures of videos
            # that are not token protected on vid.ly.
        )
        # then we need to record that we did this
        vidly_submission = VidlySubmission.objects.create(
            event=event,
            url=video_url,
            tag=tag,
            hd=True,
            submission_error=error or None
        )
        default_template = Template.objects.get(default_archive_template=True)
        # Do an in place edit in case this started before the fetch_duration
        # has started.
        Event.objects.filter(id=event.id).update(
            template=default_template,
            template_environment={'tag': tag}
        )

    return {
        'tag': vidly_submission.tag,
        'error': vidly_submission.submission_error
    }


@require_POST
@login_required
@must_be_your_event
@json_view
def event_screencaptures(request, event):
    if event.status != Event.STATUS_INITIATED:
        return http.HttpResponseBadRequest(
            "Events NOT in the state of initiated."
        )
    upload = event.upload
    video_url = upload.url

    context = {}

    cache_key = 'fetching-{0}'.format(event.id)

    # This function sets the cache `fetching-{id}` before and after calling
    # those functions in the videoinfo module.
    # The reason is that those calls might take many many seconds
    # and the webapp might send async calls to the event_picture view
    # which will inform the webapp that the slow videoinfo processes
    # are running and thus that the webapp shouldn't kick if off yet.

    seconds = event.duration
    if not event.duration:
        # it's a poor man's lock
        if not cache.get(cache_key):
            cache.set(cache_key, True, 60)
            seconds = videoinfo.fetch_duration(
                event,
                video_url=video_url,
                save=True,
                verbose=settings.DEBUG
            )
            cache.delete(cache_key)
            event = Event.objects.get(id=event.id)
    context['seconds'] = seconds
    # The reason we can't use `if event.duration:` is because the
    # fetch_duration() does an inline-update instead of modifying
    # the instance object.
    no_pictures = Picture.objects.filter(event=event).count()
    if event.duration and not no_pictures:
        if not cache.get(cache_key):
            cache.set(cache_key, True, 60)
            event = Event.objects.get(id=event.id)
            no_pictures = videoinfo.fetch_screencapture(
                event,
                video_url=video_url,
                save=True,
                verbose=settings.DEBUG,
                set_first_available=not event.picture,
                import_immediately=True,
            )
            cache.delete(cache_key)
            event = Event.objects.get(id=event.id)
    if no_pictures and not event.picture:
        # no picture has been chosen previously
        pictures = Picture.objects.filter(event=event).order_by('created')[:1]
        for picture in pictures:
            event.picture = picture
            event.save()
            break
    context['no_pictures'] = no_pictures
    return context


# Note that this view is publically available.
# That means we can't trust the content but we can take it as a hint.
@csrf_exempt
@require_POST
def vidly_media_webhook(request):
    if not request.POST.get('xml'):
        return http.HttpResponseBadRequest("no 'xml'")

    xml_string = request.POST['xml'].strip()
    try:
        struct = xmltodict.parse(xml_string)
    except ExpatError:
        return http.HttpResponseBadRequest("Bad 'xml'")

    try:
        task = struct['Response']['Result']['Task']
        try:
            vidly_submission = VidlySubmission.objects.get(
                url=task['SourceFile'],
                tag=task['MediaShortLink']
            )
            if task['Status'] == 'Finished':
                if not vidly_submission.finished:
                    vidly_submission.finished = timezone.now()
                    vidly_submission.save()

                event = vidly_submission.event

                if (
                    task['Private'] == 'false' and
                    event.privacy != Event.PRIVACY_PUBLIC
                ):
                    # the event is private but the video is not
                    vidly.update_media_protection(
                        vidly_submission.tag,
                        True  # make it private
                    )
                    if not vidly_submission.token_protection:
                        vidly_submission.token_protection = True
                        vidly_submission.save()

                # Awesome!
                # This event now has a fully working transcoded piece of
                # media.
                if event.status == Event.STATUS_PENDING:
                    event.status = Event.STATUS_SCHEDULED
                event.archive_time = timezone.now()
                event.save()

                # More awesome! We can start processing the transcoded media.
                if not event.duration:
                    videoinfo.fetch_duration(
                        event,
                        save=True,
                        verbose=settings.DEBUG
                    )
                    event = Event.objects.get(id=event.id)
                if event.duration:
                    if not Picture.objects.filter(event=event):
                        videoinfo.fetch_screencapture(
                            event,
                            save=True,
                            verbose=settings.DEBUG,
                            set_first_available=True,
                        )
            elif task['Status'] == 'Error':
                if not vidly_submission.errored:
                    vidly_submission.errored = timezone.now()
                    vidly_submission.save()
        except VidlySubmission.DoesNotExist:
            # remember, we can't trust the XML since it's publicly
            # available and exposed as a webhook
            pass

    except KeyError:
        # If it doesn't have a "Result" or "Task", it was just a notification
        # that the media was added.
        pass

    return http.HttpResponse('OK\n')


@never_cache
@login_required
@must_be_your_event
@json_view
def event_picture(request, event):

    if request.method == 'POST':
        form = forms.PictureForm(json.loads(request.body), instance=event)
        if not form.is_valid():
            return http.HttpResponseBadRequest(form.errors)
        with transaction.atomic():
            form.save()

    # if it has screen captures start returning them
    pictures = Picture.objects.filter(event=event).order_by('created')
    thumbnails = []
    # geometry = request.GET.get('geometry', '160x90')
    # crop = request.GET.get('crop', 'center')
    geometry = '160x90'
    crop = 'center'
    for p in pictures:
        thumb = get_thumbnail(
            p.file, geometry, crop=crop
        )
        picked = event.picture and event.picture == p
        thumbnails.append({
            'id': p.id,
            'url': thumb.url,
            'width': thumb.width,
            'height': thumb.height,
            'picked': picked,
            # 'large_url': large_thumb.url,
        })

    context = {}
    if thumbnails:
        context['thumbnails'] = thumbnails

    cache_key = 'fetching-{0}'.format(event.id)
    context['fetching'] = bool(cache.get(cache_key))
    return context


@never_cache
@login_required
@must_be_your_event
@json_view
def event_summary(request, event):
    return {
        'event': serialize_event(event, extended=True),
        'pictures': Picture.objects.filter(event=event).count(),
    }


def _videos_by_tags(tags):
    """Return a list of dicts where each dict looks something like this:

        {'id': 123, 'tag': 'abc123', 'Status': 'Processing', 'finished': False}

    And if there's no VidlySubmission the dict will just look like this:

        {'id': 124}

    The advantage of this function is that you only need to do 1 query
    to Vid.ly for a long list of tags.
    """
    all_results = vidly.query(tags.keys())
    video_contexts = []
    for tag, event in tags.items():
        video_context = {
            'id': event.id,
        }
        if event.duration:
            video_context['duration'] = event.duration
            video_context['duration_human'] = show_duration(event.duration)
        qs = VidlySubmission.objects.filter(event=event, tag=tag)
        for vidly_submission in qs.order_by('-submission_time')[:1]:
            video_context['tag'] = tag
            results = all_results.get(tag, {})
            video_context['status'] = results.get('Status')
            video_context['finished'] = results.get('Status') == 'Finished'
            if video_context['finished']:
                if not vidly_submission.finished:
                    vidly_submission.finished = timezone.now()
                    vidly_submission.save()
                if not event.archive_time:
                    event.archive_time = timezone.now()
                    event.save()
            elif results.get('Status') == 'Error':
                if not vidly_submission.errored:
                    vidly_submission.errored = timezone.now()
                    vidly_submission.save()
            else:
                video_context['estimated_time_left'] = (
                    vidly_submission.get_estimated_time_left()
                )
            break
        video_contexts.append(video_context)
    return video_contexts


@never_cache
@login_required
@must_be_your_event
@json_view
def event_video(request, event):
    context = {}
    tag = event.template_environment and event.template_environment.get('tag')
    if tag:
        tags = {tag: event}
        contexts = _videos_by_tags(tags)
        context = contexts[0]
    return context


@require_POST
@login_required
@json_view
def videos(request):
    """Similar to event_video except it expects a 'ids' request parameter
    and returns a dict of videos where the event ID is the keys."""
    try:
        ids = json.loads(request.body)['ids']
    except ValueError as x:
        return http.HttpResponseBadRequest(str(x))
    events = Event.objects.filter(
        id__in=ids,
        creator=request.user,
        template__name__icontains='vid.ly',
    )
    tags = {}
    for event in events:
        tag = (
            event.template_environment and
            event.template_environment.get('tag')
        )
        tags[tag] = event
    return dict(
        (x['id'], x)
        for x in _videos_by_tags(tags)
    )


@require_POST
@login_required
@must_be_your_event
@json_view
def event_publish(request, event):
    if event.status != Event.STATUS_INITIATED:
        return http.HttpResponseBadRequest("Not in an initiated state")

    groups = []

    with transaction.atomic():
        # there has to be a Vid.ly video
        if 'youtube' in event.template.name.lower():
            event.status = Event.STATUS_SCHEDULED
        else:
            tag = event.template_environment['tag']
            submission = None
            qs = VidlySubmission.objects.filter(event=event, tag=tag)
            for each in qs.order_by('-submission_time'):
                submission = each
                break
            assert submission, "Event has no vidly submission"

            results = vidly.query(tag).get(tag, {})
            # Let's check the privacy/tokenization of the video.
            # What matters (source of truth) is the event's privacy state.
            if event.privacy != Event.PRIVACY_PUBLIC and results:
                # make sure the submission the the video IS token protected
                if not submission.token_protection:
                    submission.token_protection = True
                    submission.save()
                if results['Private'] == 'false':
                    # We can only do this if the video has been successfully
                    # transcoded.
                    if results['Status'] == 'Finished':
                        vidly.update_media_protection(
                            tag,
                            True
                        )
            if results.get('Status') == 'Finished':
                event.status = Event.STATUS_SCHEDULED
                # If it's definitely finished, it means we managed to ask
                # Vid.ly this question before Vid.ly had a chance to ping
                # us on the webhook. Might as well set it now.
                if not event.archive_time:
                    event.archive_time = timezone.now()
            else:
                # vidly hasn't finished processing it yet
                event.status = Event.STATUS_PENDING
        event.save()

        if not event.picture and not event.placeholder_img:
            # assign the default placeholder picture if there is one
            try:
                event.picture = Picture.objects.get(default_placeholder=True)
                event.save()
            except Picture.DoesNotExist:  # pragma: no cover
                pass

        if not event.channels.all():
            # forcibly put it in the default channel(s)
            for channel in Channel.objects.filter(default=True):
                event.channels.add(channel)

        if not Discussion.objects.filter(event=event):
            discussion = Discussion.objects.create(
                event=event,
                enabled=True,
                notify_all=True
            )
            discussion.moderators.add(event.creator)

        if event.privacy == Event.PRIVACY_PUBLIC:
            for topic in event.topics.all():
                for group in topic.groups.all():
                    if group not in groups:
                        groups.append(group)
            for group in groups:
                Approval.objects.create(event=event, group=group)

    for group in groups:
        sending.email_about_approval_requested(
            event,
            group,
            request
        )

    return True


@never_cache
@login_required
@json_view
def your_events(request):
    # If you have some uploads that are lingering but not associated
    # with an event, we might want to create empty events for them
    # now.
    lingering_uploads = Upload.objects.filter(
        mime_type__startswith='video/',
        user=request.user,
        event__isnull=True,
        size__gt=0
    )
    with transaction.atomic():
        for upload in lingering_uploads:
            event = Event.objects.create(
                status=Event.STATUS_INITIATED,
                creator=upload.user,
                upload=upload,
                start_time=upload.created,
                privacy=Event.PRIVACY_PUBLIC,
                created=upload.created
            )
            # event.channels.add(default_channel)

            # We'll pretend the event was created at the time the
            # video was uploaded.
            # Doing this after the create() is necessary because the
            # model uses the auto_now_add=True
            event.created = upload.created
            event.save()

            upload.event = event
            upload.save()

    events = (
        Event.objects.filter(
            creator=request.user,
            status=Event.STATUS_INITIATED,
        )
        .filter(
            Q(upload__isnull=False) | Q(template__name__icontains='YouTube')
        )
        .select_related('upload', 'picture')
        .order_by('-created')
    )

    all_possible_pictures = (
        Picture.objects
        .filter(event__in=events)
        .values('event_id')
        .annotate(Count('event'))
    )
    pictures_count = {}
    for each in all_possible_pictures:
        pictures_count[each['event_id']] = each['event__count']

    serialized = []
    for event in events:
        upload = event.upload
        if upload:
            upload = {
                'size': upload.size,
                'mime_type': upload.mime_type
            }
        thumbnail = None
        if event.picture or event.placeholder_img:
            geometry = '160x90'
            crop = 'center'
            if event.picture:
                thumb = get_thumbnail(
                    event.picture.file, geometry, crop=crop
                )
            else:
                thumb = get_thumbnail(
                    event.placeholder_img, geometry, crop=crop
                )
            thumbnail = {
                'url': thumb.url,
                'width': thumb.width,
                'height': thumb.height,
            }
        serialized.append({
            'id': event.id,
            'title': event.title,
            'upload': upload,
            'picture': thumbnail,
            'pictures': pictures_count.get(event.id, 0),
            'modified': event.modified,
        })
    return {'events': serialized}


@require_POST
@login_required
@must_be_your_event
@json_view
def event_delete(request, event):
    with transaction.atomic():
        event.status = Event.STATUS_REMOVED
        event.save()
    return True


@transaction.atomic
def unsubscribe(request, identifier):
    context = {}

    cache_key = 'unsubscribe-%s' % identifier

    user_id = cache.get(cache_key)
    if user_id:
        user = get_object_or_404(User, id=user_id)
    else:
        user = None
        cache.set(cache_key, request.user.id, 60)
    context['user_'] = user

    if request.method == 'POST':
        if not user:
            return http.HttpResponseBadRequest('No user')
        user_profile = get_profile_safely(user, create_if_necessary=True)
        user_profile.optout_event_emails = True
        user_profile.save()
        cache.delete(cache_key)
        return redirect('new:unsubscribed')

    return render(request, 'new/unsubscribe.html', context)


def unsubscribed(request):
    context = {}
    return render(request, 'new/unsubscribed.html', context)


@require_POST
@login_required
@must_be_your_event
@json_view
@transaction.atomic
def event_pictures_rotate(request, event):
    try:
        post = request.body and json.loads(request.body) or {}
    except ValueError:
        return http.HttpResponseBadRequest('invalid JSON body')
    direction = post.get('direction', 'left')
    for picture in Picture.objects.filter(event=event):
        img = Image.open(picture.file.path)
        format = picture.file.name.lower().endswith('.png') and 'png' or 'jpeg'
        img = img.rotate(direction == 'left' and 90 or 270, expand=True)
        f = StringIO()
        try:
            img.save(f, format=format)
            picture.file.save(
                picture.file.name,
                ContentFile(f.getvalue())
            )
        finally:
            f.close()
    return True


@login_required
@json_view
def youtube_extract(request):
    url = request.GET.get('url')
    if not url:
        return http.HttpResponseBadRequest('No url')
    try:
        return youtube.extract_metadata_by_url(url)
    except ValueError:
        return {'error': 'Video ID not found by that URL'}
    except youtube.VideoNotFound as ex:
        return {'error': 'No video by that ID could be found (%s)' % ex}


@require_POST
@login_required
@json_view
@transaction.atomic
def youtube_create(request):
    try:
        body = json.loads(request.body)
    except ValueError:
        # it wasn't sent as a JSON request body
        return http.HttpResponseBadRequest('Missing JSON request body')
    if not body.get('id'):
        return http.HttpResponseBadRequest('Missing id')

    # extract all the details again
    data = youtube.extract_metadata_by_id(body['id'])

    for template in Template.objects.filter(name__icontains='YouTube'):
        break
    else:
        template = Template.objects.create(
            name='YouTube',
            content=(
                '<iframe width="896" height="504" src="https://www.youtube-noc'
                'ookie.com/embed/{{ id }}?rel=0&amp;showinfo=0" '
                'frameborder="0" allowfullscreen></iframe>'
            )
        )

    youtube_url = 'https://www.youtube.com/watch?v=' + data['id']
    additional_links = u'On YouTube™ {}'.format(youtube_url)

    event = Event.objects.create(
        title=data['title'],
        description=data['description'],
        template=template,
        template_environment={'id': data['id']},
        creator=request.user,
        status=Event.STATUS_INITIATED,
        privacy=Event.PRIVACY_PUBLIC,
        start_time=timezone.now(),
        additional_links=additional_links,
        archive_time=timezone.now(),
    )
    img_temp = NamedTemporaryFile(delete=True)
    img_temp.write(requests.get(data['thumbnail_url']).content)
    img_temp.flush()
    event.placeholder_img.save(
        os.path.basename(data['thumbnail_url']),
        File(img_temp)
    )
    for tag in data['tags']:
        try:
            event.tags.add(Tag.objects.get(name__iexact=tag))
        except Tag.DoesNotExist:
            event.tags.add(Tag.objects.create(name=tag))

    # first get the parent of all YouTube channels
    youtube_parent, __ = Channel.objects.get_or_create(
        name=u'YouTube™',
        slug='youtube',
        never_show=True,
    )
    try:
        channel = Channel.objects.get(
            parent=youtube_parent,
            youtube_id=data['channel']['id'],
            name=data['channel']['title'],
        )
    except Channel.DoesNotExist:
        channel = Channel.objects.create(
            parent=youtube_parent,
            youtube_id=data['channel']['id'],
            name=data['channel']['title'],
            slug=slugify(data['channel']['title'])
        )
        if data['channel']['thumbnail_url']:
            img_temp = NamedTemporaryFile(delete=True)
            img_temp.write(
                requests.get(data['channel']['thumbnail_url']).content
            )
            img_temp.flush()
            channel.image.save(
                os.path.basename(data['channel']['thumbnail_url']),
                File(img_temp)
            )
    event.channels.add(channel)
    # also put it in the other default channels
    for channel in Channel.objects.filter(default=True):
        event.channels.add(channel)
    return serialize_event(event)
