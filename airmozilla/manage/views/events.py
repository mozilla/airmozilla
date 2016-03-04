import collections
import datetime
import hashlib
import re
import urlparse
import os

import pytz
import vobject
import boto

from django.conf import settings
from django import http
from django.contrib.auth.models import User, Group, Permission
from django.core.cache import cache
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Sum, Count, Max
from django.core.exceptions import ImproperlyConfigured
from django.views.decorators.cache import cache_page
from django.core.urlresolvers import reverse

from jsonview.decorators import json_view

from airmozilla.main.templatetags.jinja_helpers import thumbnail, short_desc
from airmozilla.manage.templatetags.jinja_helpers import (
    scrub_transform_passwords,
)
from airmozilla.base import mozillians
from airmozilla.base.utils import (
    paginate,
    tz_apply,
    unhtml,
    shorten_url,
    get_base_url,
    prepare_vidly_video_url,
)
from airmozilla.main.models import (
    Approval,
    Event,
    EventTweet,
    Location,
    Template,
    Channel,
    SuggestedEvent,
    SuggestedEventComment,
    VidlySubmission,
    EventHitStats,
    EventLiveHits,
    CuratedGroup,
    EventAssignment,
    Picture,
    Chapter,
    LocationDefaultEnvironment,
)
from airmozilla.subtitles.models import AmaraVideo
from airmozilla.main.views import is_contributor
from airmozilla.manage import forms
from airmozilla.manage.tweeter import send_tweet
from airmozilla.manage import vidly
from airmozilla.manage import archiver
from airmozilla.manage import sending
from airmozilla.manage import videoinfo
from airmozilla.manage.templatetags.jinja_helpers import full_tweet_url
from airmozilla.comments.models import Discussion, Comment
from airmozilla.surveys.models import Survey
from airmozilla.uploads.models import Upload
from airmozilla.base.templatetags.jinja_helpers import show_duration
from airmozilla.base.utils import STOPWORDS
from .decorators import (
    staff_required,
    permission_required,
    superuser_required,
    cancel_redirect
)
from .utils import can_edit_event, get_var_templates


@staff_required
@permission_required('main.add_event')
@cancel_redirect('manage:events')
@transaction.atomic
def event_request(request, duplicate_id=None):
    """Event request page:  create new events to be published."""
    if (
        request.user.has_perm('main.add_event_scheduled') or
        request.user.has_perm('main.change_event_others')
    ):
        form_class = forms.EventExperiencedRequestForm
    else:
        form_class = forms.EventRequestForm

    initial = {}
    event_initial = None
    curated_groups = []

    if duplicate_id:
        # Use a blank event, but fill in the initial data from duplication_id
        event_initial = Event.objects.get(id=duplicate_id)
        try:
            discussion = Discussion.objects.get(event=event_initial)
        except Discussion.DoesNotExist:
            discussion = None

        curated_groups = CuratedGroup.objects.filter(event=event_initial)

        if discussion:
            # We need to extend the current form class with one more
            # boolean field.
            from django import forms as django_forms

            class _Form(form_class):
                enable_discussion = django_forms.BooleanField(
                    help_text=(
                        '"%s" had discussion enabled. '
                        'Duplicate that configuration?' % event_initial.title
                    )
                )

            form_class = _Form

        # We copy the initial data from a form generated on the origin event
        # to retain initial data processing, e.g., on EnvironmentField.
        event_initial_form = form_class(instance=event_initial)
        for field in event_initial_form.fields:
            if field == 'start_time':
                if event_initial.location:
                    initial['start_time'] = event_initial.location_time
                else:
                    initial['start_time'] = event_initial.start_time
                # safer to do this here
                initial['start_time'] = (
                    initial['start_time'].replace(tzinfo=None)
                )
            else:
                if field in event_initial_form.initial:
                    # Usual initial form data
                    initial[field] = event_initial_form.initial[field]
                else:
                    # Populated by form __init__ (e.g., approvals)
                    initial[field] = event_initial_form.fields[field].initial
        # Excluded fields in an event copy
        blank_fields = ('slug',)
        for field in blank_fields:
            initial[field] = ''

    if request.method == 'POST':
        event = Event()
        if request.POST.get('picture'):
            event.picture = Picture.objects.get(id=request.POST['picture'])

        if (
            duplicate_id and
            'placeholder_img' not in request.FILES and
            not request.POST.get('picture')
        ):
            # If this is a duplicate event action and a placeholder_img
            # was not provided, copy it from the duplication source.
            event.placeholder_img = event_initial.placeholder_img

        form = form_class(request.POST, request.FILES, instance=event)
        if form.is_valid():
            event = form.save(commit=False)
            _event_process(request, form, event)
            event.save()
            form.save_m2m()
            if form.cleaned_data.get('enable_discussion'):
                dup_discussion = Discussion.objects.create(
                    event=event,
                    enabled=True,
                    closed=False,
                    moderate_all=discussion.moderate_all,
                    notify_all=discussion.notify_all
                )
                for moderator in discussion.moderators.all():
                    dup_discussion.moderators.add(moderator)
            if form.cleaned_data['curated_groups']:
                for name in form.cleaned_data['curated_groups']:
                    CuratedGroup.objects.get_or_create(
                        name=name,
                        event=event
                    )
            messages.success(
                request,
                'Event <a href="{}">{}</a> created.'.format(
                    reverse('manage:event_edit', args=(event.id,)),
                    event.title,
                )
            )
            return redirect('manage:events')
    else:
        curated_groups_choices = []
        if duplicate_id and discussion:
            initial['enable_discussion'] = True
        if duplicate_id and curated_groups:
            initial['curated_groups'] = curated_groups.values_list(
                'name',
                flat=True
            )
            curated_groups_choices = [
                (x, x) for x in initial['curated_groups']
            ]
        form = form_class(
            initial=initial,
            curated_groups_choices=curated_groups_choices
        )

    context = {
        'form': form,
        'duplicate_event': event_initial,
    }
    return render(request, 'manage/event_request.html', context)


@staff_required
@permission_required('main.change_event')
def events(request):
    """Event edit/production:  approve, change, and publish events."""
    return render(request, 'manage/events.html', {})


@staff_required
@permission_required('main.change_event')
@json_view
def events_data(request):
    events = []
    qs = (
        Event.objects
        .exclude(status=Event.STATUS_INITIATED)
        .order_by('-modified')
    )
    form = forms.EventsDataForm(request.GET)
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))

    if form.cleaned_data['since']:
        qs = qs.filter(modified__gt=form.cleaned_data['since'])

    max_modified = qs.aggregate(Max('modified'))
    if max_modified['modified__max']:
        max_modified = max_modified['modified__max'].isoformat()
    else:
        max_modified = None

    _can_change_event_others = (
        request.user.has_perm('main.change_event_others')
    )
    base_filter = {}
    base_exclude = {}
    if not request.user.has_perm('main.change_event_others'):
        base_filter['creator'] = request.user
    if is_contributor(request.user):
        base_exclude['privacy'] = Event.PRIVACY_COMPANY
    qs = qs.filter(**base_filter)
    qs = qs.exclude(**base_exclude)

    event_channel_names = collections.defaultdict(list)
    _channel_names = dict(
        (x['id'], x['name'])
        for x in Channel.objects.all().values('id', 'name')
    )
    for each in Event.channels.through.objects.all().values():
        event_channel_names[each['event_id']].append(
            _channel_names[each['channel_id']]
        )

    now = timezone.now()
    live_time = now + datetime.timedelta(minutes=settings.LIVE_MARGIN)

    all_needs_approval = (
        Approval.objects
        .filter(processed=False)
        .values_list('event_id', flat=True)
    )

    pictures_counts = {}
    grouped_pictures = (
        Picture.objects
        .filter(event__in=qs)
        .values('event')
        .annotate(Count('event'))
    )
    for each in grouped_pictures:
        pictures_counts[each['event']] = each['event__count']

    if request.GET.get('limit'):
        try:
            limit = int(request.GET['limit'])
            assert limit > 0
            qs = qs[:limit]
        except (ValueError, AssertionError):
            pass

    locations = dict(
        (x.pk, x) for x in Location.objects.all()
    )
    template_names = dict(
        (x['id'], x['name'])
        for x in Template.objects.all().values('id', 'name')
    )
    for event in qs:
        event.location = locations.get(event.location_id)
        if event.location:
            start_time = event.location_time.strftime('%d %b %Y %I:%M%p')
            start_time_iso = event.location_time.isoformat()
        else:
            start_time = event.start_time.strftime('%d %b %Y %I:%M%p %Z')
            start_time_iso = event.start_time.isoformat()

        needs_approval = event.pk in all_needs_approval
        is_live = False
        is_upcoming = False
        if event.status == Event.STATUS_SCHEDULED and not needs_approval:
            if not event.archive_time and event.start_time < live_time:
                is_live = True
            elif not event.archive_time and event.start_time > live_time:
                is_upcoming = True

        row = {
            'modified': event.modified.isoformat(),
            'status': event.status,
            'status_display': event.get_status_display(),
            'privacy': event.privacy,
            'privacy_display': event.get_privacy_display(),
            'title': event.title,
            'slug': event.slug,
            'location': event.location and event.location.name or '',
            'id': event.pk,
            'start_time': start_time,
            'start_time_iso': start_time_iso,
            'channels': event_channel_names.get(event.pk, []),
            'archive_time': (
                event.archive_time.isoformat()
                if event.archive_time
                else None
            ),
            'can': [],  # actions you can take on the event
        }

        # to make the size of the JSON file as small as possible,
        # only include certain fields if they're true
        if event.status == Event.STATUS_PENDING:
            row['is_pending'] = True
        elif event.status == Event.STATUS_SCHEDULED:
            row['is_scheduled'] = True
        if is_live:
            row['is_live'] = True
        if is_upcoming:
            row['is_upcoming'] = is_upcoming
        if needs_approval:
            row['needs_approval'] = True
        if event.id in pictures_counts:
            row['pictures'] = pictures_counts[event.id]
        if event.picture_id:
            row['picture'] = event.picture_id

        if row.get('is_pending'):
            # this one is only relevant if it's pending
            template_name = template_names.get(event.template_id)
            if template_name:
                row['has_vidly_template'] = 'Vid.ly' in template_name
        if event.popcorn_url and not is_upcoming:
            row['popcorn_url'] = event.popcorn_url

        if not row.get('picture') and not event.placeholder_img:
            row['nopicture'] = True

        if _can_change_event_others:
            row['can'].append('duplicate')
            row['can'].append('archive')
            # row['archive_url'] = reverse(
            #     'manage:event_archive',
            #     args=(event.pk,)
            # )

        events.append(row)

    urls = {
        'manage:event_edit': reverse('manage:event_edit', args=('0',)),
        'manage:event_duplicate': reverse(
            'manage:event_duplicate', args=('0',)
        ),
        'manage:redirect_event_thumbnail': reverse(
            'manage:redirect_event_thumbnail', args=('0',)
        ),
        'manage:event_archive': reverse(
            'manage:event_archive', args=('0',)
        ),
        'manage:event_duplicate': reverse(
            'manage:event_duplicate', args=('0',)
        ),
        'manage:picturegallery': reverse('manage:picturegallery'),
    }

    return {'events': events, 'urls': urls, 'max_modified': max_modified}


def _event_process(request, form, event):
    """Generate and clean associated event data for an event request
       or event edit:  timezone application, approvals update and
       notifications, creator and modifier."""
    if not event.creator:
        event.creator = request.user
    event.modified_user = request.user

    if event.location:
        tz = pytz.timezone(event.location.timezone)
        event.start_time = tz_apply(event.start_time, tz)

    if 'approvals' in form.cleaned_data:
        event.save()
        approvals_old = [app.group for app in event.approval_set.all()]
        approvals_new = form.cleaned_data['approvals']
        approvals_add = set(approvals_new).difference(approvals_old)
        for approval in approvals_add:
            group = Group.objects.get(name=approval)
            app = Approval.objects.create(group=group, event=event)
            sending.email_about_approval_requested(
                event,
                group,
                request
            )
        # Note! we currently do not allow approvals
        # to be "un-requested". That's because the email has already
        # gone out and it's too late now.

        if 'curated_groups' in form.cleaned_data:
            # because this form field acts like "tags",
            # we split them by ,
            names = [
                x.strip() for x in
                form.cleaned_data['curated_groups']
                if x.strip()
            ]
            for name in names:
                all_groups = mozillians.get_all_groups(name)
                group, __ = CuratedGroup.objects.get_or_create(
                    event=event,
                    name=name
                )
                found = [x for x in all_groups if x['name'] == name]
                if found and found[0]['url'] != group.url:
                    group.url = found[0]['url']
                    group.save()

            # delete any we had before that aren't submitted any more
            (
                CuratedGroup.objects
                .filter(event=event)
                .exclude(name__in=names)
                .delete()
            )


@staff_required
@permission_required('main.change_event')
@cancel_redirect('manage:events')
@transaction.atomic
def event_edit(request, id):
    """Edit form for a particular event."""
    event = get_object_or_404(Event, id=id)
    result = can_edit_event(event, request.user)
    if isinstance(result, http.HttpResponse):
        return result
    if request.user.has_perm('main.change_event_others'):
        form_class = forms.EventEditForm
    elif request.user.has_perm('main.add_event_scheduled'):
        form_class = forms.EventExperiencedRequestForm
    else:
        form_class = forms.EventRequestForm

    curated_groups = (
        CuratedGroup.objects.filter(event=event).order_by('created')
    )

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=event)
        if form.is_valid():
            event = form.save(commit=False)
            _event_process(request, form, event)
            if not event.location:
                event.start_time = event.start_time.replace(
                    tzinfo=timezone.utc
                )
            event.save()
            form.save_m2m()
            edit_url = reverse('manage:event_edit', args=(event.pk,))
            if is_privacy_vidly_mismatch(event):
                # We'll need to update the status of token protection
                # on Vid.ly for this event.
                try:
                    vidly.update_media_protection(
                        event.template_environment['tag'],
                        event.privacy != Event.PRIVACY_PUBLIC,
                    )
                    submissions = VidlySubmission.objects.filter(
                        event=event,
                        tag=event.template_environment['tag'],
                    ).order_by('-submission_time')
                    for submission in submissions[:1]:
                        submission.token_protection = (
                            event.privacy != Event.PRIVACY_PUBLIC
                        )
                        submission.save()
                        break
                except vidly.VidlyUpdateError as x:
                    messages.error(
                        request,
                        'Video protect status could not be updated on '
                        'Vid.ly\n<code>%s</code>' % x
                    )
            messages.info(
                request,
                'Event "<a href=\"%s\">%s</a>" saved. [Edit again](%s)' % (
                    reverse('main:event', args=(event.slug,)),
                    event.title,
                    edit_url
                )
            )
            return redirect('manage:events')
    else:
        initial = {}
        initial['curated_groups'] = curated_groups.values_list(
            'name',
            flat=True
        )
        curated_groups_choices = [
            (x, x) for x in initial['curated_groups']
        ]
        form = form_class(
            instance=event,
            initial=initial,
            curated_groups_choices=curated_groups_choices,
        )

    context = {
        'form': form,
        'event': event,
        'suggested_event': None,
        'suggested_event_comments': None,
        'tweets': EventTweet.objects.filter(event=event).order_by('id'),
    }
    try:
        suggested_event = SuggestedEvent.objects.get(accepted=event)
        context['suggested_event'] = suggested_event
        context['suggested_event_comments'] = (
            SuggestedEventComment.objects
            .filter(suggested_event=suggested_event)
            .select_related('user')
            .order_by('created')
        )
    except SuggestedEvent.DoesNotExist:
        pass

    context['is_vidly_event'] = False
    if event.template and 'Vid.ly' in event.template.name:
        context['is_vidly_event'] = True
        context['vidly_submissions'] = (
            VidlySubmission.objects
            .filter(event=event)
            .order_by('-submission_time')
        )

    # Is it stuck and won't auto-archive?
    context['stuck_pending'] = False
    now = timezone.now()
    time_ago = now - datetime.timedelta(minutes=15)
    if (
        event.status == Event.STATUS_PENDING and
        event.template and
        'Vid.ly' in event.template.name and
        event.template_environment and  # can be None
        event.template_environment.get('tag') and
        not VidlySubmission.objects.filter(
            event=event,
            submission_time__gte=time_ago
        )
    ):
        tag = event.template_environment['tag']
        results = vidly.query(tag)
        status = results.get(tag, {}).get('Status')
        if status == 'Finished':
            context['stuck_pending'] = True

    try:
        discussion = Discussion.objects.get(event=event)
        context['discussion'] = discussion
        context['comments_count'] = Comment.objects.filter(event=event).count()
    except Discussion.DoesNotExist:
        context['discussion'] = None

    context['approvals'] = (
        Approval.objects
        .filter(event=event)
        .select_related('group')
    )

    context['chapters_count'] = Chapter.objects.filter(event=event).count()

    try:
        context['assignment'] = EventAssignment.objects.get(event=event)
    except EventAssignment.DoesNotExist:
        context['assignment'] = None

    amara_videos = AmaraVideo.objects.filter(event=event)
    context['amara_videos_count'] = amara_videos.count()

    try:
        context['survey'] = Survey.objects.get(events=event)
    except Survey.DoesNotExist:
        context['survey'] = None

    context['archived_hits'] = 0
    context['live_hits'] = 0

    for each in EventHitStats.objects.filter(event=event).values('total_hits'):
        context['archived_hits'] += each['total_hits']
    for each in EventLiveHits.objects.filter(event=event).values('total_hits'):
        context['live_hits'] += each['total_hits']

    context['count_event_uploads'] = Upload.objects.filter(event=event).count()

    return render(request, 'manage/event_edit.html', context)


def is_privacy_vidly_mismatch(event):
    if (
        event.template and
        'vid.ly' in event.template.name.lower() and
        event.template_environment and
        event.template_environment.get('tag')
    ):
        tag = event.template_environment.get('tag')
        statuses = vidly.query(tag)
        if tag in statuses:
            status = statuses[tag]
            public_event = event.privacy == Event.PRIVACY_PUBLIC
            public_video = status['Private'] == 'false'
            return public_event != public_video

    return False


@json_view
@staff_required
@permission_required('main.change_event')
def event_privacy_vidly_mismatch(request, id):
    event = get_object_or_404(Event, id=id)
    # first of all, the video template must be a vid.ly one
    return is_privacy_vidly_mismatch(event)


@json_view
@staff_required
@permission_required('main.change_event')
@transaction.atomic
def event_template_environment_mismatch(request, id):
    event = get_object_or_404(Event, id=id)

    location_default_environment = None
    # Check if the template_environment of this event is different
    # from that in a matched LocationDefaultEnvironment.
    if event.template and event.location:
        matches = LocationDefaultEnvironment.objects.filter(
            location=event.location,
            privacy=event.privacy,
            template=event.template
        )
        for match in matches:
            if event.template_environment != match.template_environment:
                # oh noes!
                location_default_environment = match
                break

    if request.method == 'POST':
        assert location_default_environment
        event.template_environment = (
            location_default_environment.template_environment
        )
        event.save()
        messages.success(
            request,
            'Template environment successfully changed.'
        )
        return redirect('manage:event_edit', event.id)
    else:
        if location_default_environment:
            return {
                'id': location_default_environment.id,
                'url': reverse('manage:location_edit', args=(
                    location_default_environment.location.id,
                )),
            }
    return None


@staff_required
@permission_required('main.change_event')
@cancel_redirect('manage:events')
@transaction.atomic
def event_edit_duration(request, id):
    event = get_object_or_404(Event, id=id)
    result = can_edit_event(event, request.user)
    if isinstance(result, http.HttpResponse):
        return result

    if request.method == 'POST':
        form = forms.EventDurationForm(request.POST, instance=event)
        if form.is_valid():
            event = form.save()
            # For some reason, if you pass it `duration=''` it thinks
            # you don't want to set this value, so it doesn't change
            # it. So we manually fix that for this case.
            if form.cleaned_data['duration'] is None:
                event.duration = None
                event.save()
            if event.duration:
                messages.success(
                    request,
                    'Duration set to %s' % show_duration(event.duration)
                )
            else:
                videoinfo.fetch_duration(
                    event,
                    save=True,
                    verbose=settings.DEBUG
                )
                new_duration = Event.objects.get(id=event.id).duration
                if new_duration is not None:
                    new_duration = show_duration(
                        new_duration,
                        include_seconds=True
                    )
                messages.success(
                    request,
                    'Duration re-set to %s' % new_duration
                )
            return redirect('manage:event_edit', event.id)
    else:
        form = forms.EventDurationForm(instance=event)

    context = {
        'event': event,
        'form': form,
    }
    return render(request, 'manage/event_edit_duration.html', context)


@cache_page(60)
def redirect_event_thumbnail(request, id):
    """The purpose of this is to be able to NOT have to generate the
    thumbnail for each event in the events_data() view. It makes the JSON
    smaller and makes it possible to only need the thumbnail for few
    (at a time) thumbnails that we need. """
    event = get_object_or_404(Event, id=id)
    geometry = request.GET.get('geometry', '40x40')
    crop = request.GET.get('crop', 'center')
    if event.picture:
        thumb = thumbnail(event.picture.file, geometry, crop=crop)
    else:
        thumb = thumbnail(event.placeholder_img, geometry, crop=crop)

    return redirect(thumb.url)


@require_POST
@staff_required
@permission_required('main.change_event')
@transaction.atomic
def event_stop_live(request, id):
    """Convenient thing that changes the status and redirects you to
    go and upload a file."""
    event = get_object_or_404(Event, id=id)
    event.status = Event.STATUS_PROCESSING
    event.save()

    return redirect('manage:event_upload', event.pk)


@require_POST
@superuser_required
@transaction.atomic
def event_delete(request, id):
    """Don't just delete the event record, but delete everything associated
    with it:
        * S3 Uploads
        * Pictures and their files
    """
    event = get_object_or_404(Event, id=id, status=Event.STATUS_REMOVED)

    s3_keys = {}
    for upload in Upload.objects.filter(event=event):
        key = urlparse.urlparse(upload.url).path
        s3_keys[upload.id] = key
    if s3_keys:
        conn = boto.connect_s3(
            settings.AWS_ACCESS_KEY_ID,
            settings.AWS_SECRET_ACCESS_KEY
        )
        bucket = conn.get_bucket(settings.S3_UPLOAD_BUCKET)
        for id, key in s3_keys.items():
            bucket.delete_key(key)

    no_vidly_medias = 0
    for submission in VidlySubmission.objects.filter(event=event):
        tag, error = vidly.delete_media(submission.tag)
        if not error:
            no_vidly_medias += 1
            submission.delete()

    no_pictures = 0
    for picture in Picture.objects.filter(event=event):
        # make sure it's not used by anybody else
        other_events = (
            Event.objects
            .exclude(id=event.id)
            .filter(picture=picture)
        )
        if not other_events.count():
            if os.path.isfile(picture.file.path):
                picture.delete()
                os.remove(picture.file.path)
                no_pictures += 1

    with transaction.atomic():
        event.delete()
        messages.success(
            request,
            'Event wiped off the face of the earth (%d S3 uploads, '
            '%d Vid.ly videos, %d pictures)' % (
                len(s3_keys),
                no_vidly_medias,
                no_pictures,
            )
        )
    return redirect('manage:events')


@staff_required
@permission_required('uploads.add_upload')
def event_upload(request, id):
    event = get_object_or_404(Event, id=id)
    context = {}
    context['event'] = event
    # this is used by the vidly automation
    context['vidly_submit_details'] = {
        'hd': True,
        'email': request.user.email,
        'token_protection': event.privacy != Event.PRIVACY_PUBLIC
    }
    context['event_archive_details'] = {}
    if Template.objects.filter(default_archive_template=True):
        template = Template.objects.get(default_archive_template=True)
        template_vars = get_var_templates(template)
        template_var = template_vars[0]
        if template_var.endswith('='):
            template_var = template_var[:-1]
        context['event_archive_details'].update({
            'template': template.id,
            'shortcode_key_name': template_var,
        })

    request.session['active_event'] = event.pk
    return render(request, 'manage/event_upload.html', context)


@staff_required
@cancel_redirect(lambda r, id: reverse('manage:event_edit', args=(id,)))
@permission_required('main.change_eventassignment')
def event_assignment(request, id):
    event = get_object_or_404(Event, id=id)
    context = {}
    permission_required = Permission.objects.get(codename='can_be_assigned')
    assignment, __ = EventAssignment.objects.get_or_create(event=event)
    if request.method == 'POST':
        assignment.event = event
        assignment.save()
        form = forms.EventAssignmentForm(
            instance=assignment,
            data=request.POST,
            permission_required=permission_required,
        )
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Event assignment saved.'
            )
            return redirect('manage:event_edit', event.pk)

    else:
        form = forms.EventAssignmentForm(
            instance=assignment,
            permission_required=permission_required,
        )

    context['event'] = event
    context['assignment'] = assignment
    context['form'] = form
    context['permission_required'] = permission_required
    return render(request, 'manage/event_assignment.html', context)


@staff_required
@cancel_redirect(lambda r, id: reverse('manage:event_edit', args=(id,)))
@permission_required('main.change_event')
def event_transcript(request, id):
    event = get_object_or_404(Event, id=id)
    context = {}

    from airmozilla.manage.scraper import get_urls, scrape_urls
    scrapeable_urls = list(get_urls(event.additional_links))

    if request.method == 'POST':
        form = forms.EventTranscriptForm(
            instance=event,
            data=request.POST,
        )
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Event transcript saved.'
            )
            return redirect('manage:event_edit', event.pk)
    else:
        initial = {}
        if request.GET.getlist('urls'):
            response = scrape_urls(request.GET.getlist('urls'))
            if response['text']:
                initial['transcript'] = response['text']

            errors = []
            for result in response['results']:
                if not result['worked']:
                    errors.append('%s: %s' % (result['url'], result['status']))
            if errors:
                errors.insert(0, 'Some things could not be scraped correctly')
                messages.error(
                    request,
                    '\n'.join(errors)
                )

        form = forms.EventTranscriptForm(instance=event, initial=initial)

    amara_videos = AmaraVideo.objects.filter(event=event)

    context['event'] = event
    context['amara_videos'] = amara_videos
    context['form'] = form
    context['scrapeable_urls'] = scrapeable_urls
    return render(request, 'manage/event_transcript.html', context)


@superuser_required
def event_vidly_submissions(request, id):
    event = get_object_or_404(Event, id=id)
    submissions = (
        VidlySubmission.objects
        .filter(event=event)
        .order_by('submission_time')
    )

    if request.method == 'POST':
        ids = request.POST.getlist('id')
        forced = request.POST.get('forced')
        submissions = submissions.filter(id__in=ids)
        if not forced:
            submissions = submissions.filter(tag__isnull=False)
        # if any of those have tag that we're currently using, raise a 400
        current_tag = event.template_environment.get('tag')
        if current_tag and submissions.filter(tag=current_tag):
            return http.HttpResponseBadRequest(
                "Can not delete because it's in use"
            )
        deletions = failures = 0
        for submission in submissions:
            if submission.tag:
                results = vidly.delete_media(submission.tag)
            else:
                assert forced
                results = ''
            if forced or submission.tag in results:
                submission.delete()
                deletions += 1
            else:
                failures += 1
        messages.success(
            request,
            "%s vidly submissions deleted. %s failures" % (
                deletions,
                failures
            )
        )
        return redirect('manage:event_vidly_submissions', event.id)

    paged = paginate(submissions, request.GET.get('page'), 20)

    active_submission = None
    try:
        te = event.template_environment
        if te and te.get('tag'):
            active_submission = submissions.get(
                tag=te['tag']
            )
    except VidlySubmission.DoesNotExist:  # pragma: no cover
        pass

    data = {
        'paginate': paged,
        'event': event,
        'active_submission': active_submission,
    }
    return render(request, 'manage/event_vidly_submissions.html', data)


@superuser_required
@json_view
def event_vidly_submission(request, id, submission_id):

    def as_fields(result):
        return [
            {'key': a, 'value': b}
            for (a, b)
            in sorted(result.items())
        ]

    event = get_object_or_404(Event, id=id)
    submission = get_object_or_404(
        VidlySubmission,
        event=event,
        id=submission_id,
    )
    data = {
        'url': submission.url,
        'email': submission.email,
        'hd': submission.hd,
        'token_protection': submission.token_protection,
        'submission_error': submission.submission_error,
        'submission_time': submission.submission_time.isoformat(),
    }
    if request.GET.get('as_fields'):
        return {'fields': as_fields(data)}
    return data


@superuser_required
@require_POST
@transaction.atomic
def event_archive_auto(request, id):
    event = get_object_or_404(Event, id=id)
    assert 'Vid.ly' in event.template.name
    assert event.template_environment.get('tag')
    archiver.archive(event)
    messages.info(
        request, "Archiving started for this event"
    )
    url = reverse('manage:event_edit', args=(event.pk,))
    return redirect(url)


@staff_required
@permission_required('main.change_event')
@transaction.atomic
def event_tweets(request, id):
    """Summary of tweets and submission of tweets"""
    data = {}
    event = get_object_or_404(Event, id=id)

    if request.method == 'POST':
        if request.POST.get('cancel'):
            tweet = get_object_or_404(
                EventTweet,
                pk=request.POST.get('cancel')
            )
            tweet.delete()
            messages.info(request, 'Tweet cancelled')
        elif request.POST.get('send'):
            tweet = get_object_or_404(
                EventTweet,
                pk=request.POST.get('send')
            )
            send_tweet(tweet)
            if tweet.error:
                messages.warning(request, 'Failed to send tweet!')
            else:
                messages.info(request, 'Tweet sent!')
        elif request.POST.get('error'):
            if not request.user.is_superuser:
                return http.HttpResponseForbidden(
                    'Only available for superusers'
                )
            tweet = get_object_or_404(
                EventTweet,
                pk=request.POST.get('error')
            )
            return http.HttpResponse(tweet.error, content_type='text/plain')
        else:
            raise NotImplementedError
        url = reverse('manage:event_tweets', args=(event.pk,))
        return redirect(url)

    data['event'] = event
    data['tweets'] = EventTweet.objects.filter(event=event).order_by('id')

    return render(request, 'manage/event_tweets.html', data)


@staff_required
@permission_required('main.change_event')
@cancel_redirect(lambda r, id: reverse('manage:event_tweets', args=(id,)))
@transaction.atomic
def new_event_tweet(request, id):
    context = {}
    event = get_object_or_404(Event, id=id)

    if request.method == 'POST':
        form = forms.EventTweetForm(event, data=request.POST)
        if form.is_valid():
            event_tweet = form.save(commit=False)
            # The send_date is automatically assigned on the event.
            # If the user didn't try to set it, it gets a default date
            # with a timezone. All is well.
            # If you did try to set it and used non-timezone-human-text
            # to try to set it we have to correct it for you.
            # This is basically because we need to store with timezone
            # but we can't expect our users to type in timezone information
            # on the string they're entering into the input field.
            if event_tweet.send_date and form.cleaned_data['send_date']:
                assert event.location, "event must have a location"
                tz = pytz.timezone(event.location.timezone)
                event_tweet.send_date = tz_apply(event_tweet.send_date, tz)
            else:
                event_tweet.send_date = timezone.now()
            event_tweet.event = event
            event_tweet.creator = request.user
            event_tweet.save()
            messages.info(request, 'Tweet saved')
            url = reverse('manage:event_edit', args=(event.pk,))
            return redirect(url)
    else:
        initial = {}
        event_url = reverse('main:event', args=(event.slug,))
        base_url = get_base_url(request)
        abs_url = urlparse.urljoin(base_url, event_url)
        try:
            abs_url = shorten_url(abs_url)
            context['shortener_error'] = None
        except (ImproperlyConfigured, ValueError) as err:  # pragma: no cover
            context['shortener_error'] = str(err)

        initial['text'] = unhtml('%s\n%s' % (short_desc(event), abs_url))
        initial['include_placeholder'] = bool(event.placeholder_img)
        if event.start_time > timezone.now():
            if event.location:
                start_time = event.location_time
            else:
                start_time = event.start_time
            initial['send_date'] = (start_time - datetime.timedelta(
                minutes=30
            )).strftime('%Y-%m-%d %H:%M')

        form = forms.EventTweetForm(initial=initial, event=event)

        if event.start_time > timezone.now():
            if event.location:
                event.location.timezone
                start_time = event.location_time
                start_time = start_time.strftime('%Y-%m-%d %H:%M')
            else:
                # this'll display it with full timezone information
                start_time = str(event.start_time)
            form.fields['send_date'].help_text += (
                " Note! This event starts %s" % (
                    start_time,
                )
            )

    context['event'] = event
    context['form'] = form
    context['tweets'] = EventTweet.objects.filter(event=event)

    return render(request, 'manage/new_event_tweet.html', context)


@staff_required
@permission_required('main.change_event')
@cancel_redirect(
    lambda r, id, tweet_id: reverse('manage:event_tweets', args=(id,))
)
@transaction.atomic
def edit_event_tweet(request, id, tweet_id):
    tweet = get_object_or_404(EventTweet, event__id=id, id=tweet_id)
    if request.method == 'POST':
        form = forms.EventTweetForm(
            data=request.POST,
            instance=tweet,
            event=tweet.event
        )
        if form.is_valid():
            tweet = form.save()
            messages.success(request, 'Tweet saved')
            return redirect('manage:event_tweets', tweet.event.id)
    else:
        form = forms.EventTweetForm(instance=tweet, event=tweet.event)

    context = {
        'form': form,
        'event': tweet.event,
        'tweet': tweet,
    }
    return render(request, 'manage/edit_event_tweet.html', context)


@staff_required
@permission_required('main.change_event')
def all_event_tweets(request):
    """Summary of tweets and submission of tweets"""
    return render(request, 'manage/all_event_tweets.html')


@staff_required
@permission_required('main.change_event')
@json_view
def all_event_tweets_data(request):
    """Summary of tweets and submission of tweets (the data)"""
    context = {}
    tweets_qs = (
        EventTweet.objects
        .filter()
        .select_related('event')
        .order_by('-send_date')
    )
    tweets = []
    for tweet in tweets_qs.select_related('event', 'creator'):
        each = {
            'id': tweet.id,
            'text': tweet.text,
            'tweet_id': tweet.tweet_id,
            'failed_attempts': tweet.failed_attempts,
            'send_date': tweet.send_date.isoformat(),
            'sent_date': (
                tweet.sent_date and tweet.sent_date.isoformat() or None
            ),
            'event': {
                'pk': tweet.event.pk,
                'title': tweet.event.title,
                '_is_scheduled': tweet.event.is_scheduled(),
                '_needs_approval': tweet.event.needs_approval(),
            },
        }
        if tweet.creator:
            each['creator'] = {
                'email': tweet.creator.email,
            }
        if tweet.tweet_id:
            each['full_tweet_url'] = full_tweet_url(tweet.tweet_id)
        tweets.append(each)
    context['tweets'] = tweets
    context['urls'] = {
        'manage:event_edit': reverse('manage:event_edit', args=(0,)),
        'manage:event_tweets': reverse('manage:event_tweets', args=(0,)),
    }
    return context


@staff_required
@permission_required('main.change_event_others')
@cancel_redirect('manage:events')
@transaction.atomic
def event_archive(request, id):
    """Dedicated page for setting page template (archive) and archive time."""
    event = get_object_or_404(Event, id=id)
    if request.method == 'POST':
        form = forms.EventArchiveForm(request.POST, instance=event)
        if form.is_valid():
            event = form.save(commit=False)

            def has_successful_vidly_submission(event):
                submissions = VidlySubmission.objects.filter(event=event)
                for submission in submissions.order_by('-submission_time')[:1]:
                    tag = submission.tag
                    results = vidly.query(tag).get(tag, {})
                    return results.get('Status') == 'Finished'

                return False

            if (
                event.has_vidly_template() and
                not has_successful_vidly_submission(event)
            ):
                # some events go from live -> to transcoding -> to archived
                # and others go right away from transcoding -> to archived
                # this IF makes sure the event is not currently transcoding
                # before its status changes to PENDING
                if event.status != Event.STATUS_PROCESSING:
                    event.status = Event.STATUS_PENDING
            else:
                event.status = Event.STATUS_SCHEDULED
                now = (
                    timezone.now()
                )
                # add one second otherwise, it will not appear on the
                # event manager immediately after the redirect
                event.archive_time = now - datetime.timedelta(seconds=1)
            event.save()
            messages.info(request, 'Event "%s" saved.' % event.title)
            return redirect('manage:events')
    else:
        form = forms.EventArchiveForm(instance=event)

    initial = {'hd': True}
    if event.privacy != Event.PRIVACY_PUBLIC:
        initial['token_protection'] = True
    if event.upload:
        initial['url'] = event.upload.url
    else:
        try:
            suggested_event = SuggestedEvent.objects.get(accepted=event)
            if suggested_event.upload:
                initial['url'] = suggested_event.upload.url
        except SuggestedEvent.DoesNotExist:
            pass

    vidly_shortcut_form = forms.VidlyURLForm(
        initial=initial,
        disable_token_protection=event.privacy != Event.PRIVACY_PUBLIC
    )

    for template in Template.objects.filter(default_archive_template=True):
        default_archive_template = template
        break
    else:
        default_archive_template = None

    context = {
        'form': form,
        'event': event,
        'vidly_shortcut_form': vidly_shortcut_form,
        'default_archive_template': default_archive_template,
    }
    return render(request, 'manage/event_archive.html', context)


@superuser_required
@cancel_redirect(lambda r, id: reverse('manage:event_edit', args=(id,)))
@transaction.atomic
def event_archive_time(request, id):
    event = get_object_or_404(Event, id=id)
    if request.method == 'POST':
        form = forms.EventArchiveTimeForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.info(request, 'Event archive time saved.')
            return redirect('manage:event_edit', event.id)
    else:
        form = forms.EventArchiveTimeForm(instance=event)
    context = {
        'form': form,
        'event': event,
    }
    return render(request, 'manage/event_archive_time.html', context)


@require_POST
@transaction.atomic
@json_view
def event_fetch_duration(request, id):
    event = get_object_or_404(Event, id=id)
    duration = event.duration
    if not event.duration and event.upload:
        duration = videoinfo.fetch_duration(
            event,
            video_url=event.upload.url,
            save=True,
            verbose=settings.DEBUG
        )

    return {'duration': duration}


@require_POST
@transaction.atomic
@json_view
def event_fetch_screencaptures(request, id):
    event = get_object_or_404(Event, id=id)
    pictures = Picture.objects.filter(event=event).count()
    if not pictures and event.duration and event.upload:
        pictures = videoinfo.fetch_screencapture(
            event,
            video_url=event.upload.url,
            save=True,
            verbose=settings.DEBUG,
        )

    return {'pictures': pictures}


@staff_required
@permission_required('main.add_event')
def event_hit_stats(request):

    possible_order_by = ('total_hits', 'hits_per_day', 'score')
    order_by = request.GET.get('order')
    if order_by not in possible_order_by:
        order_by = possible_order_by[-1]

    include_excluded = bool(request.GET.get('include_excluded'))
    today = timezone.now()
    yesterday = today - datetime.timedelta(days=1)
    title = request.GET.get('title')
    stats = (
        EventHitStats.objects
        .exclude(event__archive_time__isnull=True)
        .filter(event__archive_time__lt=yesterday)
        .order_by('-%s' % order_by)
        .extra(select={
            'hits_per_day': 'total_hits / extract(days from (now() '
                            '- main_event.archive_time))',
            'score': '(featured::int + 1) * total_hits'
                     '/ extract(days from (now() - archive_time)) ^ 1.8',
        })
        .select_related('event')
    )

    if title:
        stats = stats.filter(event__title__icontains=title)

    if not include_excluded:
        stats = stats.exclude(event__channels__exclude_from_trending=True)

    stats_total = (
        EventHitStats.objects
        .filter(event__archive_time__isnull=False)
        .aggregate(Sum('total_hits'))
    )
    stats_total = stats_total['total_hits__sum']

    events_total = (
        Event.objects
        .filter(archive_time__isnull=False)
        .filter(template__name__contains='Vid.ly')
        .count()
    )

    paged = paginate(stats, request.GET.get('page'), 20)
    data = {
        'order_by': order_by,
        'paginate': paged,
        'stats_total': stats_total,
        'events_total': events_total,
        'include_excluded': include_excluded,
        'title': title,
    }
    return render(request, 'manage/event_hit_stats.html', data)


@staff_required
@permission_required('comments.change_discussion')
@transaction.atomic
def event_discussion(request, id):
    context = {}
    event = get_object_or_404(Event, id=id)
    try:
        discussion = Discussion.objects.get(event=event)
    except Discussion.DoesNotExist:
        discussion = None

    if request.method == 'POST':
        if request.POST.get('cancel'):
            return redirect('manage:event_edit', event.pk)

        form = forms.DiscussionForm(
            request.POST,
            instance=discussion
        )
        if form.is_valid():
            discussion = form.save(commit=False)
            discussion.event = event
            discussion.save()
            discussion.moderators.clear()
            for user in form.cleaned_data['moderators']:
                discussion.moderators.add(user)
            messages.success(
                request,
                'Discussion saved'
            )
            return redirect('manage:event_discussion', event.pk)
    else:
        initial = {}
        if not discussion:
            initial['enabled'] = True
            initial['moderate_all'] = True
            initial['notify_all'] = True
        form = forms.DiscussionForm(
            instance=discussion,
            initial=initial
        )

    if not discussion:
        messages.warning(
            request,
            "No discussion configuration previously set up. "
            "This functions the same as if the discussion is not enabled."
        )

    context['event'] = event
    context['discussion'] = discussion
    form.fields['closed'].help_text = (
        "Comments posted appears but not possible to post more comments"
    )
    form.fields['moderate_all'].help_text = (
        "Every posted comment must be moderated before being made public"
    )
    form.fields['notify_all'].help_text = (
        "All moderators get an email notification for every posted comment"
    )
    form.fields['moderators'].help_text = (
        "Users who have the ability to approve comments"
    )
    _users = (
        User.objects
        .filter(is_active=True)
        .extra(select={'lower_email': 'lower(email)'})
        .order_by('lower_email')
    )
    form.fields['moderators'].choices = [
        (x.pk, x.email)
        for x in _users
    ]
    context['form'] = form

    comments_base_url = reverse('manage:event_comments', args=(event.pk,))
    _comments = Comment.objects.filter(event=event)
    context['counts'] = []
    context['counts'].append(('All', comments_base_url, _comments.count()))
    _counts = {}
    for each in _comments.values('status').annotate(Count('status')):
        _counts[each['status']] = each['status__count']
    for status, label in Comment.STATUS_CHOICES:
        url = comments_base_url + '?status=%s' % status
        context['counts'].append(
            (label, url, _counts.get(status, 0))
        )
    flagged_url = comments_base_url + '?flagged=1'
    context['counts'].append(
        ('Flagged', flagged_url, _comments.filter(flagged__gt=0).count())
    )
    return render(request, 'manage/event_discussion.html', context)


@staff_required
@permission_required('comments.change_comment')
def event_comments(request, id):
    context = {}
    event = get_object_or_404(Event, id=id)
    context['event'] = event
    comments = Comment.objects.filter(event=event)
    form = forms.CommentsFilterForm(request.GET)
    filtered = False
    if form.is_valid():
        if form.cleaned_data['status'] == 'flagged':
            comments = comments.filter(flagged__gt=0)
            filtered = True
        elif form.cleaned_data['status']:
            comments = comments.filter(status=form.cleaned_data['status'])
            filtered = True
        if form.cleaned_data['user']:
            user_filter = (
                Q(user__email__icontains=form.cleaned_data['user']) |
                Q(user__first_name__icontains=form.cleaned_data['user']) |
                Q(user__last_name__icontains=form.cleaned_data['user'])
            )
            comments = comments.filter(user_filter)
            filtered = True
        if form.cleaned_data['comment']:
            comments = comments.filter(
                comment__icontains=form.cleaned_data['comment']
            )
            filtered = True

    context['count'] = comments.count()
    paged = paginate(comments, request.GET.get('page'), 10)
    context['paginate'] = paged
    context['form'] = form
    context['filtered'] = filtered
    return render(request, 'manage/comments.html', context)


@json_view
@staff_required
def event_assignments(request):
    context = {}
    assigned_users = []
    _users_count = collections.defaultdict(int)
    for each in EventAssignment.users.through.objects.all().values():
        _users_count[each['user_id']] += 1
    users = User.objects.filter(pk__in=_users_count.keys()).order_by('email')

    class _AssignedUser(object):
        def __init__(self, user, count):
            self.user = user
            self.count = count

    for user in users:
        assigned_users.append(
            _AssignedUser(
                user,
                _users_count[user.pk]
            )
        )
    context['assigned_users'] = assigned_users

    events = []
    now = timezone.now()
    qs = (
        Event.objects
        .exclude(status=Event.STATUS_REMOVED)
        .filter(start_time__gte=now)
    )
    for event in qs.order_by('start_time'):
        try:
            assignment = EventAssignment.objects.get(event=event)
            assignment = {
                'users': assignment.users.all().order_by('email'),
                'locations': assignment.locations.all().order_by('name'),
            }
        except EventAssignment.DoesNotExist:
            assignment = {
                'users': [],
                'locations': []
            }
        event._assignments = assignment
        events.append(event)
    context['events'] = events

    return render(request, 'manage/event_assignments.html', context)


def event_assignments_ical(request):
    cache_key = 'event_assignements_ical'
    assignee = request.GET.get('assignee')

    if assignee:
        assignee = get_object_or_404(User, email=assignee)
        cache_key += str(assignee.pk)

    cached = cache.get(cache_key)
    if cached:
        # additional response headers aren't remembered so add them again
        cached['Access-Control-Allow-Origin'] = '*'
        return cached

    cal = vobject.iCalendar()

    now = timezone.now()
    base_qs = EventAssignment.objects.all().order_by('-event__start_time')
    if assignee:
        base_qs = base_qs.filter(users=assignee)

    title = 'Airmo'
    if assignee:
        title += ' for %s' % assignee.email
    else:
        title += ' crew assignments'

    cal.add('X-WR-CALNAME').value = title
    assignments = list(
        base_qs
        .filter(event__start_time__lt=now)
        [:settings.CALENDAR_SIZE]
    )
    assignments += list(
        base_qs
        .filter(event__start_time__gte=now)
    )
    base_url = get_base_url(request)

    for assignment in assignments:
        event = assignment.event
        vevent = cal.add('vevent')
        vevent.add('summary').value = "[AirMo crew] %s" % event.title

        # Adjusted start times for Event Assignment iCal feeds
        # to allow staff sufficient time for event set-up.
        vevent.add('dtstart').value = (
            event.start_time - datetime.timedelta(minutes=30)
        )
        vevent.add('dtend').value = (
            event.start_time + datetime.timedelta(
                seconds=event.estimated_duration
            )
        )
        emails = [u.email for u in assignment.users.all().order_by('email')]
        vevent.add('description').value = 'Assigned to: ' + ', '.join(emails)

        locations = []
        if event.location:
            locations.append(event.location.name)
        locations.extend([
            x.name for x in assignment.locations.all().order_by('name')
        ])
        locations.sort()
        vevent.add('location').value = ', '.join(locations)
        vevent.add('url').value = (
            base_url + reverse('main:event', args=(event.slug,))
        )
    icalstream = cal.serialize()
    # return http.HttpResponse(icalstream,
    #                          content_type='text/plain; charset=utf-8')
    response = http.HttpResponse(icalstream,
                                 content_type='text/calendar; charset=utf-8')
    filename = 'AirMozillaEventAssignments'
    filename += '.ics'
    response['Content-Disposition'] = (
        'inline; filename=%s' % filename)
    cache.set(cache_key, response, 60 * 10)  # 10 minutes

    # https://bugzilla.mozilla.org/show_bug.cgi?id=909516
    response['Access-Control-Allow-Origin'] = '*'

    return response


@staff_required
@permission_required('main.change_event')
@cancel_redirect(lambda r, id: reverse('manage:event_edit', args=(id,)))
@transaction.atomic
def event_survey(request, id):
    event = get_object_or_404(Event, id=id)
    survey = None

    if request.method == 'POST':
        form = forms.EventSurveyForm(request.POST)
        if form.is_valid():
            survey_id = int(form.cleaned_data['survey'])
            Survey.events.through.objects.filter(event=event).delete()
            if survey_id:
                survey = Survey.objects.get(id=survey_id)
                survey.events.add(event)
                messages.info(
                    request,
                    'Event associated with survey'
                )
            else:
                messages.info(
                    request,
                    'Event disassociated with survey'
                )

            return redirect('manage:event_edit', event.id)
    else:
        initial = {}
        try:
            survey_events, = Survey.events.through.objects.filter(event=event)
            survey = survey_events.survey
            initial['survey'] = survey.id
        except ValueError:
            # not associated with any survey
            initial['survey'] = 0

        form = forms.EventSurveyForm(initial=initial)
    context = {
        'event': event,
        'surveys': Survey.objects.all(),
        'form': form,
        'survey': survey,
    }
    return render(request, 'manage/event_survey.html', context)


@require_POST
@staff_required
@permission_required('main.change_event_others')
@json_view
def vidly_url_to_shortcode(request, id):
    event = get_object_or_404(Event, id=id)
    form = forms.VidlyURLForm(data=request.POST)
    if form.is_valid():
        url = form.cleaned_data['url']
        if event.privacy != Event.PRIVACY_PUBLIC:
            # forced
            token_protection = True
        else:
            token_protection = form.cleaned_data['token_protection']
        hd = form.cleaned_data['hd']

        base_url = get_base_url(request)
        webhook_url = base_url + reverse('manage:vidly_media_webhook')

        url = prepare_vidly_video_url(url)

        shortcode, error = vidly.add_media(
            url,
            token_protection=token_protection,
            hd=hd,
            notify_url=webhook_url,
        )
        VidlySubmission.objects.create(
            event=event,
            url=url,
            token_protection=token_protection,
            hd=hd,
            tag=shortcode,
            submission_error=error
        )
        url_scrubbed = scrub_transform_passwords(url)
        if shortcode:
            return {'shortcode': shortcode, 'url': url_scrubbed}
        else:
            return http.HttpResponseBadRequest(error)
    return http.HttpResponseBadRequest(str(form.errors))


@staff_required
@json_view
def event_autocomplete(request):
    form = forms.EventsAutocompleteForm(request.GET)
    if not form.is_valid():
        return http.HttpResponseBadRequest(str(form.errors))
    max_results = form.cleaned_data['max'] or 10
    query = form.cleaned_data['q']
    query = query.lower()
    if len(query) < 2:
        return []

    _cache_key = 'autocomplete:%s' % hashlib.md5(query).hexdigest()
    result = cache.get(_cache_key)
    if result:
        return result

    patterns = cache.get('autocomplete:patterns')
    directory = cache.get('autocomplete:directory')
    if patterns is None or directory is None:
        patterns = collections.defaultdict(list)
        directory = {}
        for pk, title in Event.objects.all().values_list('id', 'title'):
            directory[pk] = title
            for word in re.split('[^\w]+', title.lower()):
                if word in STOPWORDS:
                    continue
                patterns[word].append(pk)
        cache.set('autocomplete:patterns', patterns, 60 * 60 * 24)
        cache.set('autocomplete:directory', directory, 60 * 60 * 24)

    pks = set()
    _search = re.compile('^%s' % re.escape(query))
    for key in patterns.iterkeys():
        if _search.match(key):
            pks.update(patterns[key])
            if len(pks) > max_results:
                break

    # get rid of dups
    titles = set([directory[x] for x in pks])
    # sort
    titles = sorted(titles)
    # chop
    titles = titles[:max_results]

    # save it for later
    cache.set(_cache_key, titles, 60)
    return titles
