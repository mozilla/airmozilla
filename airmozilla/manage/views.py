import collections
import datetime
import hashlib
import functools
import logging
import re
import uuid
import urlparse
import warnings
import json

from django.conf import settings
from django import http
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User, Group, Permission
from django.core.cache import cache
from django.contrib import messages
from django.core.mail import EmailMessage
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Max, Sum, Count
from django.contrib.flatpages.models import FlatPage
from django.utils.timezone import utc
from django.contrib.sites.models import RequestSite
from django.core.exceptions import ImproperlyConfigured
from django.views.decorators.cache import cache_page

import pytz
from funfactory.urlresolvers import reverse
from jinja2 import Environment, meta
import vobject
from jsonview.decorators import json_view

from airmozilla.main.helpers import thumbnail, short_desc
from airmozilla.manage.helpers import scrub_transform_passwords
from airmozilla.manage.utils import filename_to_notes
from airmozilla.base import mozillians
from airmozilla.base.utils import (
    paginate,
    tz_apply,
    unhtml,
    shorten_url,
    dot_dict
)
from airmozilla.main.models import (
    Approval,
    Event,
    EventTweet,
    Location,
    Participant,
    Tag,
    Template,
    Channel,
    SuggestedEvent,
    SuggestedEventComment,
    VidlySubmission,
    URLMatch,
    URLTransform,
    EventHitStats,
    CuratedGroup,
    EventAssignment,
    LocationDefaultEnvironment,
    RecruitmentMessage,
    Picture,
    EventRevision
)
from airmozilla.subtitles.models import AmaraVideo
from airmozilla.main.views import is_contributor
from airmozilla.manage import forms
from airmozilla.manage.tweeter import send_tweet
from airmozilla.manage import vidly
from airmozilla.manage import url_transformer
from airmozilla.manage import archiver
from airmozilla.manage import sending
from airmozilla.comments.models import Discussion, Comment, SuggestedDiscussion
from airmozilla.surveys.models import Survey, Question
from airmozilla.search.models import LoggedSearch
from airmozilla.cronlogger.models import CronLog

staff_required = user_passes_test(lambda u: u.is_staff)
superuser_required = user_passes_test(lambda u: u.is_superuser)

STOPWORDS = (
    "a able about across after all almost also am among an and "
    "any are as at be because been but by can cannot could dear "
    "did do does either else ever every for from get got had has "
    "have he her hers him his how however i if in into is it its "
    "just least let like likely may me might most must my "
    "neither no nor not of off often on only or other our own "
    "rather said say says she should since so some than that the "
    "their them then there these they this tis to too twas us "
    "wants was we were what when where which while who whom why "
    "will with would yet you your".split()
)


def permission_required(perm):
    if settings.DEBUG:  # pragma: no cover
        ct, codename = perm.split('.', 1)
        if not Permission.objects.filter(
            content_type__app_label=ct,
            codename=codename
        ):
            warnings.warn(
                "No known permission called %r" % perm,
                UserWarning,
                2
            )

    def inner_render(fn):
        @functools.wraps(fn)
        def wrapped(request, *args, **kwargs):
            # if you're not even authenticated, redirect to /login
            if not request.user.has_perm(perm):
                request.session['failed_permission'] = perm
                return redirect(reverse('manage:insufficient_permissions'))
            return fn(request, *args, **kwargs)
        return wrapped
    return inner_render


def cancel_redirect(redirect_view):
    """Redirect wrapper for POST requests which contain a cancel field."""
    def inner_render(fn):
        @functools.wraps(fn)
        def wrapped(request, *args, **kwargs):
            if request.method == 'POST' and 'cancel' in request.POST:
                if callable(redirect_view):
                    url = redirect_view(request, *args, **kwargs)
                else:
                    url = reverse(redirect_view)
                return redirect(url)
            return fn(request, *args, **kwargs)
        return wrapped
    return inner_render


@staff_required
def dashboard(request):
    """Management home / explanation page."""
    return render(request, 'manage/dashboard.html')


@staff_required
@json_view
def dashboard_data(request):
    context = {}
    now = datetime.datetime.utcnow().replace(tzinfo=utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - datetime.timedelta(days=1)
    this_week = today - datetime.timedelta(days=today.weekday())
    last_week = this_week - datetime.timedelta(days=7)
    this_month = today.replace(day=1)
    last_month = (this_month - datetime.timedelta(days=1)).replace(day=1)
    this_year = this_month.replace(month=1)
    last_year = this_year.replace(year=this_year.year - 1)
    context['groups'] = []

    def get_counts(qs, key):
        counts = {}

        def make_filter(gte=None, lt=None):
            filter = {}
            if gte is not None:
                filter['%s__gte' % key] = gte
            if lt is not None:
                filter['%s__lt' % key] = lt
            return filter

        counts['today'] = qs.filter(**make_filter(gte=today)).count()
        counts['yesterday'] = qs.filter(
            **make_filter(gte=yesterday, lt=today)).count()

        counts['this_week'] = qs.filter(**make_filter(gte=this_week)).count()
        counts['last_week'] = qs.filter(
            **make_filter(gte=last_week, lt=this_week)).count()

        counts['this_month'] = qs.filter(**make_filter(gte=this_month)).count()
        counts['last_month'] = qs.filter(
            **make_filter(gte=last_month, lt=this_month)).count()

        counts['this_year'] = qs.filter(**make_filter(gte=this_year)).count()
        counts['last_year'] = qs.filter(
            **make_filter(gte=last_year, lt=this_year)).count()

        counts['ever'] = qs.count()
        return counts

    # Events
    events = Event.objects.exclude(status=Event.STATUS_REMOVED)
    counts = get_counts(events, 'start_time')
    context['groups'].append({
        'name': 'New Events',
        'counts': counts
    })

    # Suggested Events
    counts = get_counts(SuggestedEvent.objects.all(), 'created')
    context['groups'].append({
        'name': 'Requested Events',
        'counts': counts
    })

    # Users
    counts = get_counts(User.objects.all(), 'date_joined')
    context['groups'].append({
        'name': 'New Users',
        'counts': counts
    })

    # Comments
    counts = get_counts(Comment.objects.all(), 'created')
    context['groups'].append({
        'name': 'Comments',
        'counts': counts
    })

    # Event revisions
    counts = get_counts(EventRevision.objects.all(), 'created')
    context['groups'].append({
        'name': 'Event Revisions',
        'counts': counts
    })

    # Pictures
    counts = get_counts(Picture.objects.all(), 'created')
    context['groups'].append({
        'name': 'Pictures',
        'counts': counts
    })

    def get_duration_totals(qs):

        key = 'start_time'

        def make_filter(gte=None, lt=None):
            filter = {}
            if gte is not None:
                filter['%s__gte' % key] = gte
            if lt is not None:
                filter['%s__lt' % key] = lt
            return filter

        counts = {}

        def sum(elements):
            seconds = elements.aggregate(Sum('duration'))['duration__sum']
            seconds = seconds or 0  # in case it's None
            minutes = seconds / 60
            hours = minutes / 60
            if hours > 1:
                return "%dh" % hours
            elif minutes > 1:
                return "%dm" % minutes
            return "%ds" % seconds

        counts['today'] = sum(qs.filter(**make_filter(gte=today)))
        counts['yesterday'] = sum(qs.filter(
            **make_filter(gte=yesterday, lt=today)))

        counts['this_week'] = sum(qs.filter(**make_filter(gte=this_week)))
        counts['last_week'] = sum(qs.filter(
            **make_filter(gte=last_week, lt=this_week)))

        counts['this_month'] = sum(qs.filter(**make_filter(gte=this_month)))
        counts['last_month'] = sum(qs.filter(
            **make_filter(gte=last_month, lt=this_month)))

        counts['this_year'] = sum(qs.filter(**make_filter(gte=this_year)))
        counts['last_year'] = sum(qs.filter(
            **make_filter(gte=last_year, lt=this_year)))

        counts['ever'] = sum(qs)
        return counts

    # Exceptional
    counts = get_duration_totals(Event.objects.exclude(duration__isnull=True))
    context['groups'].append({
        'name': 'Total Event Durations',
        'counts': counts
    })

    return context


@staff_required
@permission_required('auth.change_user')
def users(request):
    """User editor:  view users and update a user's group."""
    _mozilla_email_filter = (
        Q(email__endswith='@%s' % settings.ALLOWED_BID[0])
    )
    for other in settings.ALLOWED_BID[1:]:
        _mozilla_email_filter |= (
            Q(email__endswith='@%s' % other)
        )
    users_stats = {
        'total': User.objects.all().count(),
        'total_mozilla_email': (
            User.objects.filter(_mozilla_email_filter).count()
        ),
    }
    form = forms.UserFindForm()
    context = {
        'form': form,
        'users_stats': users_stats,
    }
    return render(request, 'manage/users.html', context)


@staff_required
@permission_required('auth.change_user')
@json_view
def users_data(request):
    context = {}
    users = cache.get('_get_all_users')

    if users is None:
        users = _get_all_users()
        # this is invalidated in models.py
        cache.set('_get_all_users', users, 60 * 60)

    context['users'] = users
    context['urls'] = {
        'manage:user_edit': reverse('manage:user_edit', args=('0',))
    }

    return context


def _get_all_users():
    groups = {}
    for group in Group.objects.all().values('id', 'name'):
        groups[group['id']] = group['name']

    groups_map = collections.defaultdict(list)
    for x in User.groups.through.objects.all().values('user_id', 'group_id'):
        groups_map[x['user_id']].append(groups[x['group_id']])

    users = []
    qs = User.objects.all()
    values = (
        'email',
        'id',
        'last_login',
        'is_staff',
        'is_active',
        'is_superuser'
    )
    for user_dict in qs.values(*values):
        user = dot_dict(user_dict)
        domain = user.email.split('@')[1]
        item = {
            'id': user.id,
            'email': user.email,
            'last_login': user.last_login.isoformat(),
        }
        # The reason we only add these if they're true is because we want
        # to minimize the amount of JSON we return. It works because in
        # javascript, doing `if (thing.something)` works equally if it
        # exists and is false or if it does not exist.
        if user.is_staff:
            item['is_staff'] = True
        if user.is_superuser:
            item['is_superuser'] = True
        if domain not in settings.ALLOWED_BID:
            item['is_contributor'] = True
        if not user.is_active:
            item['is_inactive'] = True
        if groups_map[user.id]:
            item['groups'] = groups_map[user.id]

        users.append(item)
    return users


@staff_required
@permission_required('auth.change_user')
@cancel_redirect('manage:users')
@transaction.commit_on_success
def user_edit(request, id):
    """Editing an individual user."""
    user = User.objects.get(id=id)
    if request.method == 'POST':
        form = forms.UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.info(request, 'User %s saved.' % user.email)
            return redirect('manage:users')
    else:
        form = forms.UserEditForm(instance=user)
    return render(request, 'manage/user_edit.html',
                  {'form': form, 'user': user})


@staff_required
@permission_required('auth.change_group')
def groups(request):
    """Group editor: view groups and change group permissions."""
    groups = Group.objects.all()
    return render(request, 'manage/groups.html', {'groups': groups})


@staff_required
@permission_required('auth.change_group')
@cancel_redirect('manage:groups')
@transaction.commit_on_success
def group_edit(request, id):
    """Edit an individual group."""
    group = Group.objects.get(id=id)
    if request.method == 'POST':
        form = forms.GroupEditForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.info(request, 'Group "%s" saved.' % group.name)
            return redirect('manage:groups')
    else:
        form = forms.GroupEditForm(instance=group)
    return render(request, 'manage/group_edit.html',
                  {'form': form, 'group': group})


@staff_required
@permission_required('auth.add_group')
@transaction.commit_on_success
def group_new(request):
    """Add a new group."""
    group = Group()
    if request.method == 'POST':
        form = forms.GroupEditForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, 'Group "%s" created.' % group.name)
            return redirect('manage:groups')
    else:
        form = forms.GroupEditForm(instance=group)
    return render(request, 'manage/group_new.html', {'form': form})


@staff_required
@permission_required('auth.delete_group')
@transaction.commit_on_success
def group_remove(request, id):
    if request.method == 'POST':
        group = Group.objects.get(id=id)
        group.delete()
        messages.info(request, 'Group "%s" removed.' % group.name)
    return redirect('manage:groups')


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
                form.cleaned_data['curated_groups'].split(',')
                if x.strip()
            ]
            if names:
                all = mozillians.get_all_groups_cached()
            for name in names:
                group, __ = CuratedGroup.objects.get_or_create(
                    event=event,
                    name=name
                )
                found = [x for x in all if x['name'] == name]
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
@permission_required('main.add_event')
@cancel_redirect('manage:events')
@transaction.commit_on_success
def event_request(request, duplicate_id=None):
    """Event request page:  create new events to be published."""
    if (request.user.has_perm('main.add_event_scheduled')
            or request.user.has_perm('main.change_event_others')):
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

            messages.success(request,
                             'Event "%s" created.' % event.title)
            return redirect('manage:events')
    else:
        if duplicate_id and discussion:
            initial['enable_discussion'] = True
        if duplicate_id and curated_groups:
            initial['curated_groups'] = ', '.join(
                x.name for x in curated_groups
            )
        form = form_class(initial=initial)

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
        Event.objects.all()
        .order_by('-modified')
    )
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

    now = datetime.datetime.utcnow().replace(tzinfo=utc)
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
        if event.mozillian:
            row['mozillian'] = event.mozillian
        if event.id in pictures_counts:
            row['pictures'] = pictures_counts[event.id]

        if row.get('is_pending'):
            # this one is only relevant if it's pending
            template_name = template_names.get(event.template_id)
            if template_name:
                row['has_vidly_template'] = 'Vid.ly' in template_name
        if event.popcorn_url and not is_upcoming:
            row['popcorn_url'] = event.popcorn_url

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

    return {'events': events, 'urls': urls}


def can_edit_event(event, user, default='manage:events'):
    if (not user.has_perm('main.change_event_others') and
            user != event.creator):
        return redirect(default)
    if event.privacy == Event.PRIVACY_COMPANY and is_contributor(user):
        return redirect(default)
    elif (
        CuratedGroup.objects.filter(event=event)
        and is_contributor(user)
    ):
        # Editing this event requires that you're also part of that curated
        # group.
        curated_group_names = [
            x[0] for x in
            CuratedGroup.objects.filter(event=event).values_list('name')
        ]
        if not mozillians.in_groups(
            user.email,
            curated_group_names
        ):
            return redirect(default)


@staff_required
@permission_required('main.change_event')
@cancel_redirect('manage:events')
@transaction.commit_on_success
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
            event.save()
            form.save_m2m()
            edit_url = reverse('manage:event_edit', args=(event.pk,))
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
        timezone.activate(pytz.timezone('UTC'))
        initial = {}
        initial['timezone'] = timezone.get_current_timezone()  # UTC
        initial['curated_groups'] = ','.join(
            x[0] for x in curated_groups.values_list('name')
        )
        form = form_class(instance=event, initial=initial)

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
    now = datetime.datetime.utcnow().replace(tzinfo=utc)
    time_ago = now - datetime.timedelta(minutes=15)
    if (
        event.status == Event.STATUS_PENDING
        and event.template
        and 'Vid.ly' in event.template.name
        and event.template_environment  # can be None
        and event.template_environment.get('tag')
        and not VidlySubmission.objects.filter(
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

    context['total_hits'] = 0

    for each in EventHitStats.objects.filter(event=event).values('total_hits'):
        context['total_hits'] += each['total_hits']

    return render(request, 'manage/event_edit.html', context)


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
@transaction.commit_on_success
def event_stop_live(request, id):
    """Convenient thing that changes the status and redirects you to
    go and upload a file."""
    event = get_object_or_404(Event, id=id)
    event.status = Event.STATUS_PENDING
    event.save()

    return redirect('manage:event_upload', event.pk)


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
    assignment, __ = EventAssignment.objects.get_or_create(event=event)
    if request.method == 'POST':
        assignment.event = event
        assignment.save()
        form = forms.EventAssignmentForm(
            instance=assignment,
            data=request.POST
        )
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Event assignment saved.'
            )
            return redirect('manage:event_edit', event.pk)

    else:
        form = forms.EventAssignmentForm(instance=assignment)

    context['event'] = event
    context['assignment'] = assignment
    context['form'] = form
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
        submissions = submissions.filter(id__in=ids, tag__isnull=False)
        # if any of those have tag that we're currently using, raise a 400
        current_tag = event.template_environment.get('tag')
        if current_tag and submissions.filter(tag=current_tag):
            return http.HttpResponseBadRequest(
                "not not delete because it's in use"
            )
        deletions = failures = 0
        for submission in submissions:
            results = vidly.delete_media(submission.tag)
            if submission.tag in results:
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

    data = {
        'paginate': paged,
        'event': event,
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
@transaction.commit_on_success
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
@transaction.commit_on_success
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
            return http.HttpResponse(tweet.error, mimetype='text/plain')
        else:
            raise NotImplementedError
        url = reverse('manage:event_tweets', args=(event.pk,))
        return redirect(url)

    data['event'] = event
    data['tweets'] = EventTweet.objects.filter(event=event).order_by('id')

    return render(request, 'manage/event_tweets.html', data)


@staff_required
@permission_required('main.change_event')
@cancel_redirect('manage:events')
@transaction.commit_on_success
def new_event_tweet(request, id):
    data = {}
    event = get_object_or_404(Event, id=id)

    if request.method == 'POST':
        form = forms.EventTweetForm(event, data=request.POST)
        if form.is_valid():
            event_tweet = form.save(commit=False)
            if event_tweet.send_date:
                assert event.location, "event must have a location"
                tz = pytz.timezone(event.location.timezone)
                event_tweet.send_date = tz_apply(event_tweet.send_date, tz)
            else:
                now = datetime.datetime.utcnow().replace(tzinfo=utc)
                event_tweet.send_date = now
            event_tweet.event = event
            event_tweet.creator = request.user
            event_tweet.save()
            messages.info(request, 'Tweet saved')
            url = reverse('manage:event_edit', args=(event.pk,))
            return redirect(url)
    else:
        initial = {}
        event_url = reverse('main:event', args=(event.slug,))
        base_url = (
            '%s://%s' % (request.is_secure() and 'https' or 'http',
                         RequestSite(request).domain)
        )
        abs_url = urlparse.urljoin(base_url, event_url)
        try:
            abs_url = shorten_url(abs_url)
            data['shortener_error'] = None
        except (ImproperlyConfigured, ValueError) as err:
            data['shortener_error'] = str(err)
        # except OtherHttpRelatedErrors?
        #    data['shortener_error'] = "Network error trying to shorten URL"

        initial['text'] = unhtml('%s\n%s' % (short_desc(event), abs_url))
        initial['include_placeholder'] = bool(event.placeholder_img)
        initial['send_date'] = ''
        form = forms.EventTweetForm(initial=initial, event=event)

    data['event'] = event
    data['form'] = form
    data['tweets'] = EventTweet.objects.filter(event=event)

    return render(request, 'manage/new_event_tweet.html', data)


@staff_required
@permission_required('main.change_event')
@transaction.commit_on_success
def all_event_tweets(request):
    """Summary of tweets and submission of tweets"""
    tweets = (
        EventTweet.objects
        .filter()
        .select_related('event')
        .order_by('-send_date')
    )
    paged = paginate(tweets, request.GET.get('page'), 10)
    data = {
        'paginate': paged,
    }

    return render(request, 'manage/all_event_tweets.html', data)


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


@staff_required
@permission_required('main.add_event')
@json_view
def participant_autocomplete(request):
    """Participant names to Event request/edit autocompleter."""
    query = request.GET['q']
    if not query:
        return {'participants': []}
    participants = Participant.objects.filter(name__icontains=query)
    # Only match names with a component which starts with the query
    regex = re.compile(r'\b%s' % re.escape(query.split()[0]), re.I)
    participant_names = [{'id': p.name, 'text': p.name}
                         for p in participants if regex.findall(p.name)]
    return {'participants': participant_names[:5]}


@staff_required
@permission_required('main.change_event_others')
@cancel_redirect('manage:events')
@transaction.commit_on_success
def event_archive(request, id):
    """Dedicated page for setting page template (archive) and archive time."""
    event = Event.objects.get(id=id)
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
                event.status = Event.STATUS_PENDING
            else:
                event.status = Event.STATUS_SCHEDULED
                now = (
                    datetime.datetime.utcnow()
                    .replace(tzinfo=utc, microsecond=0)
                )
                # add one second otherwise, it will not appear on the
                # event manager immediately after the redirect
                event.archive_time = now - datetime.timedelta(seconds=1)
            event.save()
            messages.info(request, 'Event "%s" saved.' % event.title)
            return redirect('manage:events')
    else:
        form = forms.EventArchiveForm(instance=event)
    initial = dict(email=request.user.email)
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


@staff_required
@permission_required('main.change_participant')
def participants(request):
    """Participants page:  view and search participants/speakers."""
    if request.method == 'POST':
        search_form = forms.ParticipantFindForm(request.POST)
        if search_form.is_valid():
            participants = Participant.objects.filter(
                name__icontains=search_form.cleaned_data['name']
            )
        else:
            participants = Participant.objects.all()
    else:
        participants = Participant.objects.exclude(
            cleared=Participant.CLEARED_NO
        )
        search_form = forms.ParticipantFindForm()
    participants_not_clear = Participant.objects.filter(
        cleared=Participant.CLEARED_NO
    )
    participants_paged = paginate(participants, request.GET.get('page'), 10)
    return render(request, 'manage/participants.html',
                  {'participants_clear': participants_paged,
                   'participants_not_clear': participants_not_clear,
                   'form': search_form})


@staff_required
@permission_required('main.change_participant')
@cancel_redirect('manage:participants')
@transaction.commit_on_success
def participant_edit(request, id):
    """Participant edit page:  update biographical info."""
    participant = Participant.objects.get(id=id)
    if (not request.user.has_perm('main.change_participant_others') and
            participant.creator != request.user):
        return redirect('manage:participants')
    if request.method == 'POST':
        form = forms.ParticipantEditForm(request.POST, request.FILES,
                                         instance=participant)
        if form.is_valid():
            form.save()
            messages.info(request,
                          'Participant "%s" saved.' % participant.name)
            if 'sendmail' in request.POST:
                return redirect('manage:participant_email', id=participant.id)
            return redirect('manage:participants')
    else:
        form = forms.ParticipantEditForm(instance=participant)
    return render(request, 'manage/participant_edit.html',
                  {'form': form, 'participant': participant})


@staff_required
@permission_required('main.delete_participant')
@transaction.commit_on_success
def participant_remove(request, id):
    if request.method == 'POST':
        participant = Participant.objects.get(id=id)
        if (not request.user.has_perm('main.change_participant_others') and
                participant.creator != request.user):
            return redirect('manage:participants')
        participant.delete()
        messages.info(request, 'Participant "%s" removed.' % participant.name)
    return redirect('manage:participants')


@staff_required
@permission_required('main.change_participant')
@cancel_redirect('manage:participants')
def participant_email(request, id):
    """Dedicated page for sending an email to a Participant."""
    participant = Participant.objects.get(id=id)
    if (not request.user.has_perm('main.change_participant_others') and
            participant.creator != request.user):
        return redirect('manage:participants')
    if not participant.clear_token:
        participant.clear_token = str(uuid.uuid4())
        participant.save()
    to_addr = participant.email
    from_addr = settings.EMAIL_FROM_ADDRESS
    reply_to = request.user.email
    if not reply_to:
        reply_to = from_addr
    last_events = (Event.objects.filter(participants=participant)
                        .order_by('-created'))
    last_event = last_events[0] if last_events else None
    cc_addr = last_event.creator.email if last_event else None
    subject = ('Presenter profile on Air Mozilla (%s)' % participant.name)
    token_url = request.build_absolute_uri(
        reverse('main:participant_clear',
                kwargs={'clear_token': participant.clear_token})
    )
    message = render_to_string(
        'manage/_email_participant.html',
        {
            'reply_to': reply_to,
            'token_url': token_url
        }
    )
    if request.method == 'POST':
        cc = [cc_addr] if (('cc' in request.POST) and cc_addr) else None
        email = EmailMessage(
            subject,
            message,
            'Air Mozilla <%s>' % from_addr,
            [to_addr],
            cc=cc,
            headers={'Reply-To': reply_to}
        )
        email.send()
        messages.success(request, 'Email sent to %s.' % to_addr)
        return redirect('manage:participants')
    else:
        return render(request, 'manage/participant_email.html',
                      {'participant': participant, 'message': message,
                       'subject': subject, 'reply_to': reply_to,
                       'to_addr': to_addr, 'from_addr': from_addr,
                       'cc_addr': cc_addr, 'last_event': last_event})


@staff_required
@permission_required('main.add_participant')
@cancel_redirect('manage:participants')
@transaction.commit_on_success
def participant_new(request):
    if request.method == 'POST':
        form = forms.ParticipantEditForm(request.POST, request.FILES,
                                         instance=Participant())
        if form.is_valid():
            participant = form.save(commit=False)
            participant.creator = request.user
            participant.save()
            messages.success(request,
                             'Participant "%s" created.' % participant.name)
            return redirect('manage:participants')
    else:
        form = forms.ParticipantEditForm()
    return render(request, 'manage/participant_new.html',
                  {'form': form})


@staff_required
@permission_required('main.change_channel')
def channels(request):
    channels = Channel.objects.all()
    return render(request, 'manage/channels.html',
                  {'channels': channels})


@staff_required
@permission_required('main.add_channel')
@cancel_redirect('manage:channels')
@transaction.commit_on_success
def channel_new(request):
    use_ace = bool(int(request.GET.get('use_ace', 1)))
    if request.method == 'POST':
        form = forms.ChannelForm(request.POST, instance=Channel())
        if form.is_valid():
            form.save()
            messages.success(request, 'Channel created.')
            return redirect('manage:channels')
    else:
        form = forms.ChannelForm()
    return render(request,
                  'manage/channel_new.html',
                  {'form': form,
                   'use_ace': use_ace})


@staff_required
@permission_required('main.change_channel')
@cancel_redirect('manage:channels')
@transaction.commit_on_success
def channel_edit(request, id):
    channel = Channel.objects.get(id=id)
    use_ace = bool(int(request.GET.get('use_ace', 1)))
    if request.method == 'POST':
        form = forms.ChannelForm(request.POST, request.FILES, instance=channel)
        if form.is_valid():
            channel = form.save()
            messages.info(request, 'Channel "%s" saved.' % channel.name)
            return redirect('manage:channels')
    else:
        form = forms.ChannelForm(instance=channel)
    return render(request, 'manage/channel_edit.html',
                  {'form': form, 'channel': channel,
                   'use_ace': use_ace})


@staff_required
@permission_required('main.delete_channel')
@transaction.commit_on_success
def channel_remove(request, id):
    if request.method == 'POST':
        channel = Channel.objects.get(id=id)
        channel.delete()
        messages.info(request, 'Channel "%s" removed.' % channel.name)
    return redirect('manage:channels')


def get_var_templates(template):
    env = Environment()
    ast = env.parse(template.content)

    exceptions = ('vidly_tokenize', 'edgecast_tokenize', 'popcorn_url')
    undeclared_variables = [x for x in meta.find_undeclared_variables(ast)
                            if x not in exceptions]
    return ["%s=" % v for v in undeclared_variables]


@staff_required
@permission_required('main.change_template')
@json_view
def template_env_autofill(request):
    """JSON response containing undefined variables in the requested template.
       Provides template for filling in environment."""
    template_id = request.GET['template']
    template = Template.objects.get(id=template_id)
    var_templates = get_var_templates(template)

    return {'variables': '\n'.join(var_templates)}


@staff_required
@permission_required('main.change_template')
def templates(request):
    context = {}
    context['templates'] = Template.objects.all()

    def count_events_with_template(template):
        return Event.objects.filter(template=template).count()

    context['count_events_with_template'] = count_events_with_template
    return render(request, 'manage/templates.html', context)


@staff_required
@permission_required('main.change_template')
@cancel_redirect('manage:templates')
@transaction.commit_on_success
def template_edit(request, id):
    template = Template.objects.get(id=id)
    if request.method == 'POST':
        form = forms.TemplateEditForm(request.POST, instance=template)
        if form.is_valid():
            template = form.save()
            if template.default_popcorn_template:
                others = (
                    Template.objects.filter(default_popcorn_template=True)
                    .exclude(pk=template.pk)
                )
                for other_template in others:
                    other_template.default_popcorn_template = False
                    other_template.save()
            if template.default_archive_template:
                others = (
                    Template.objects.filter(default_archive_template=True)
                    .exclude(pk=template.pk)
                )
                for other_template in others:
                    other_template.default_archive_template = False
                    other_template.save()

            messages.info(request, 'Template "%s" saved.' % template.name)
            return redirect('manage:templates')
    else:
        form = forms.TemplateEditForm(instance=template)
    return render(request, 'manage/template_edit.html', {'form': form,
                                                         'template': template})


@staff_required
@permission_required('main.add_template')
@cancel_redirect('manage:templates')
@transaction.commit_on_success
def template_new(request):
    if request.method == 'POST':
        form = forms.TemplateEditForm(request.POST, instance=Template())
        if form.is_valid():
            form.save()
            messages.success(request, 'Template created.')
            return redirect('manage:templates')
    else:
        form = forms.TemplateEditForm()
    return render(request, 'manage/template_new.html', {'form': form})


@staff_required
@permission_required('main.delete_template')
@transaction.commit_on_success
def template_remove(request, id):
    if request.method == 'POST':
        template = Template.objects.get(id=id)
        template.delete()
        messages.info(request, 'Template "%s" removed.' % template.name)
    return redirect('manage:templates')


@staff_required
@permission_required('main.change_location')
def locations(request):
    context = {}
    locations = Location.objects.all()
    context['locations'] = locations

    associated_events = collections.defaultdict(int)
    associated_suggested_events = collections.defaultdict(int)

    events = Event.objects.exclude(location__isnull=True)
    for each in events.values('location_id'):
        associated_events[each['location_id']] += 1

    suggested_events = SuggestedEvent.objects.exclude(location__isnull=True)
    for each in suggested_events.values('location_id'):
        associated_suggested_events[each['location_id']] += 1

    context['associated_events'] = associated_events
    context['associated_suggested_events'] = associated_suggested_events

    return render(request, 'manage/locations.html', context)


@staff_required
@permission_required('main.change_location')
@cancel_redirect('manage:locations')
@transaction.commit_on_success
def location_edit(request, id):
    location = get_object_or_404(Location, id=id)

    if request.method == 'POST' and request.POST.get('delete'):
        LocationDefaultEnvironment.objects.get(
            id=request.POST.get('delete'),
            location=location
        ).delete()
        messages.info(request, 'Configuration deleted.')
        return redirect('manage:location_edit', location.id)

    if request.method == 'POST' and not request.POST.get('default'):
        form = forms.LocationEditForm(request.POST, instance=location)
        if form.is_valid():
            form.save()
            messages.info(request, 'Location "%s" saved.' % location)
            return redirect('manage:locations')
    else:
        form = forms.LocationEditForm(instance=location)

    if request.method == 'POST' and request.POST.get('default'):

        default_environment_form = forms.LocationDefaultEnvironmentForm(
            request.POST
        )
        if default_environment_form.is_valid():
            fc = default_environment_form.cleaned_data

            if LocationDefaultEnvironment.objects.filter(
                location=location,
                privacy=fc['privacy']
            ):
                # there can only be one of them
                lde = LocationDefaultEnvironment.objects.get(
                    location=location,
                    privacy=fc['privacy']
                )
                lde.template = fc['template']
            else:
                lde = LocationDefaultEnvironment.objects.create(
                    location=location,
                    privacy=fc['privacy'],
                    template=fc['template']
                )
            lde.template_environment = fc['template_environment']
            lde.save()
            messages.info(request, 'Default location environment saved.')
            return redirect('manage:location_edit', location.id)
    else:
        default_environment_form = forms.LocationDefaultEnvironmentForm()

    context = {
        'form': form,
        'location': location,
        'default_environment_form': default_environment_form
    }

    context['location_default_environments'] = (
        LocationDefaultEnvironment.objects
        .filter(location=location).order_by('privacy', 'template')
    )

    return render(request, 'manage/location_edit.html', context)


@staff_required
@permission_required('main.add_location')
@cancel_redirect('manage:events')
@transaction.commit_on_success
def location_new(request):
    if request.method == 'POST':
        form = forms.LocationEditForm(request.POST, instance=Location())
        if form.is_valid():
            form.save()
            messages.success(request, 'Location created.')
            return redirect('manage:locations')
    else:
        form = forms.LocationEditForm()
    return render(request, 'manage/location_new.html', {'form': form})


@staff_required
@permission_required('main.delete_location')
@transaction.commit_on_success
def location_remove(request, id):
    location = get_object_or_404(Location, id=id)
    if request.method == 'POST':
        # This is only allowed if there are no events or suggested events
        # associated with this location
        if (
            Event.objects.filter(location=location) or
            SuggestedEvent.objects.filter(location=location)
        ):
            return http.HttpResponseBadRequest("Still being used")

        location.delete()
        messages.info(request, 'Location "%s" removed.' % location.name)
    return redirect('manage:locations')


@staff_required
@json_view
def location_timezone(request):
    """Responds with the timezone for the requested Location.  Used to
       auto-fill the timezone form in event requests/edits."""
    if not request.GET.get('location'):
        raise http.Http404('no location')
    location = get_object_or_404(Location, id=request.GET['location'])
    return {'timezone': location.timezone}


@staff_required
@permission_required('main.change_approval')
def approvals(request):
    user = request.user
    groups = user.groups.all()
    if groups.count():
        approvals = (Approval.objects.filter(
            group__in=user.groups.all(),
            processed=False)
            .exclude(event__status=Event.STATUS_REMOVED)
        )
        recent = (Approval.objects.filter(
            group__in=user.groups.all(),
            processed=True)
            .order_by('-processed_time')[:25]
        ).select_related('event', 'user', 'group')
    else:
        approvals = recent = Approval.objects.none()

    def get_suggested_event(event):
        """return the original suggested event or None"""
        try:
            return SuggestedEvent.objects.get(accepted=event)
        except SuggestedEvent.DoesNotExist:
            pass

    context = {
        'approvals': approvals,
        'recent': recent,
        'user_groups': groups,
        'get_suggested_event': get_suggested_event,
    }
    return render(request, 'manage/approvals.html', context)


@staff_required
@permission_required('main.change_approval')
@transaction.commit_on_success
def approval_review(request, id):
    """Approve/deny an event on behalf of a group."""
    approval = get_object_or_404(Approval, id=id)
    if approval.group not in request.user.groups.all():
        return redirect('manage:approvals')
    if request.method == 'POST':
        form = forms.ApprovalForm(request.POST, instance=approval)
        approval = form.save(commit=False)
        approval.approved = 'approve' in request.POST
        approval.processed = True
        approval.user = request.user
        approval.save()
        messages.info(request, '"%s" approval saved.' % approval.event.title)
        return redirect('manage:approvals')
    else:
        form = forms.ApprovalForm(instance=approval)

    context = {'approval': approval, 'form': form}
    try:
        suggested_event = SuggestedEvent.objects.get(accepted=approval.event)
    except SuggestedEvent.DoesNotExist:
        suggested_event = None
    context['suggested_event'] = suggested_event
    return render(request, 'manage/approval_review.html', context)


@require_POST
@staff_required
@permission_required('main.change_approval')
@transaction.commit_on_success
def approval_reconsider(request):
    id = request.POST.get('id')
    if not id:
        return http.HttpResponseBadRequest('no id')
    try:
        approval = get_object_or_404(Approval, id=id)
    except ValueError:
        return http.HttpResponseBadRequest('invalid id')
    approval.processed = False
    approval.approved = False
    approval.comment = ''
    approval.save()

    return redirect('manage:approvals')


@staff_required
@permission_required('flatpages.change_flatpage')
def flatpages(request):
    flatpages_paged = paginate(FlatPage.objects.all(),
                               request.GET.get('page'), 10)
    return render(request, 'manage/flatpages.html',
                  {'paginate': flatpages_paged})


@staff_required
@permission_required('flatpages.change_flatpage')
@cancel_redirect('manage:flatpages')
@transaction.commit_on_success
def flatpage_new(request):
    if request.method == 'POST':
        form = forms.FlatPageEditForm(request.POST, instance=FlatPage())
        if form.is_valid():
            instance = form.save()
            instance.sites.add(settings.SITE_ID)
            instance.save()
            if instance.url.startswith('sidebar_'):
                __, location, channel_slug = instance.url.split('_', 2)
                channel = Channel.objects.get(
                    slug=channel_slug
                )
                instance.title = 'Sidebar (%s) %s' % (location, channel.name)
                instance.save()
            messages.success(request, 'Page created.')
            return redirect('manage:flatpages')
    else:
        form = forms.FlatPageEditForm()
        form.fields['url'].help_text = (
            "for example '/my-page' or 'sidebar_top_main' (see below)"
        )
    return render(
        request,
        'manage/flatpage_new.html',
        {'form': form,
         'channels': Channel.objects.all().order_by('slug')}
    )


@staff_required
@permission_required('flatpages.change_flatpage')
@cancel_redirect('manage:flatpages')
@transaction.commit_on_success
def flatpage_edit(request, id):
    """Editing an flatpage."""
    page = FlatPage.objects.get(id=id)
    if request.method == 'POST':
        form = forms.FlatPageEditForm(request.POST, instance=page)
        if form.is_valid():
            instance = form.save()
            if instance.url.startswith('sidebar_'):
                __, location, channel_slug = instance.url.split('_', 2)
                channel = Channel.objects.get(
                    slug=channel_slug
                )
                instance.title = 'Sidebar (%s) %s' % (location, channel.name)
                instance.save()
            messages.info(request, 'Page %s saved.' % page.url)
            return redirect('manage:flatpages')
    else:
        form = forms.FlatPageEditForm(instance=page)
    return render(request, 'manage/flatpage_edit.html',
                  {'form': form, 'flatpage': page})


@staff_required
@permission_required('flatpages.delete_flatpage')
@transaction.commit_on_success
def flatpage_remove(request, id):
    if request.method == 'POST':
        flatpage = FlatPage.objects.get(id=id)
        flatpage.delete()
        messages.info(request, 'Page "%s" removed.' % flatpage.title)
    return redirect('manage:flatpages')


@require_POST
@staff_required
@permission_required('main.change_event_others')
@json_view
def vidly_url_to_shortcode(request, id):
    event = get_object_or_404(Event, id=id)
    form = forms.VidlyURLForm(data=request.POST)
    if form.is_valid():
        url = form.cleaned_data['url']
        email = form.cleaned_data['email']
        if event.privacy != Event.PRIVACY_PUBLIC:
            # forced
            token_protection = True
        else:
            token_protection = form.cleaned_data['token_protection']
        hd = form.cleaned_data['hd']
        shortcode, error = vidly.add_media(
            url,
            email=email,
            token_protection=token_protection,
            hd=hd,
        )
        VidlySubmission.objects.create(
            event=event,
            url=url,
            email=email,
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
@permission_required('main.add_event')
def suggestions(request):
    context = {}
    events = (
        SuggestedEvent.objects
        .filter(accepted=None)
        .exclude(first_submitted=None)
        .order_by('submitted')
    )
    context['include_old'] = request.GET.get('include_old')
    if not context['include_old']:
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        then = now - datetime.timedelta(days=30)
        events = events.filter(first_submitted__gte=then)

    context['events'] = events
    return render(request, 'manage/suggestions.html', context)


@staff_required
@permission_required('main.add_event')
@transaction.commit_on_success
def suggestion_review(request, id):
    event = get_object_or_404(SuggestedEvent, pk=id)
    real_event_form = None
    comment_form = forms.SuggestedEventCommentForm()

    if request.method == 'POST':

        if not event.submitted:
            return http.HttpResponseBadRequest('Not submitted')

        form = forms.AcceptSuggestedEventForm(
            request.POST,
            instance=event,
        )

        if request.POST.get('save_comment'):
            comment_form = forms.SuggestedEventCommentForm(data=request.POST)
            if comment_form.is_valid():
                comment = SuggestedEventComment.objects.create(
                    comment=comment_form.cleaned_data['comment'].strip(),
                    user=request.user,
                    suggested_event=event
                )
                sending.email_about_suggestion_comment(
                    comment,
                    request.user,
                    request
                )
                messages.info(
                    request,
                    'Comment added and %s notified.' % comment.user.email
                )
                return redirect('manage:suggestion_review', event.pk)

        reject = request.POST.get('reject')
        if reject:
            form.fields['review_comments'].required = True

        if not request.POST.get('save_comment') and form.is_valid():
            form.save()
            if reject:
                event.submitted = None
                event.status = SuggestedEvent.STATUS_REJECTED
                event.save()
                sending.email_about_rejected_suggestion(
                    event,
                    request.user,
                    request
                )
                messages.info(
                    request,
                    'Suggested event bounced back and %s has been emailed'
                    % (event.user.email,)
                )
                url = reverse('manage:suggestions')
                return redirect(url)
            else:
                dict_event = {
                    'title': event.title,
                    'description': event.description,
                    'short_description': event.short_description,
                    'start_time': event.start_time,
                    'timezone': event.location.timezone,
                    'location': event.location.pk,
                    'channels': [x.pk for x in event.channels.all()],
                    'call_info': event.call_info,
                    'privacy': event.privacy,
                    'popcorn_url': event.popcorn_url,
                }
                if dict_event['popcorn_url'] == 'https://':
                    dict_event['popcorn_url'] = ''
                real_event_form = forms.EventRequestForm(
                    data=dict_event,
                )
                real_event_form.fields['placeholder_img'].required = False
                if real_event_form.is_valid():
                    real = real_event_form.save(commit=False)
                    real.placeholder_img = event.placeholder_img
                    real.picture = event.picture
                    real.slug = event.slug
                    real.additional_links = event.additional_links
                    real.remote_presenters = event.remote_presenters
                    real.creator = request.user
                    if real.popcorn_url and not event.upcoming:
                        real.archive_time = real.start_time
                    if event.upcoming:
                        # perhaps we have a default location template
                        # environment
                        if real.location:
                            try:
                                default = (
                                    LocationDefaultEnvironment.objects
                                    .get(
                                        location=real.location,
                                        privacy=real.privacy
                                    )
                                )
                                real.template = default.template
                                real.template_environment = (
                                    default.template_environment
                                )
                            except LocationDefaultEnvironment.DoesNotExist:
                                pass
                    else:
                        real.status = Event.STATUS_PENDING
                    real.save()
                    [real.tags.add(x) for x in event.tags.all()]
                    [real.channels.add(x) for x in event.channels.all()]
                    event.accepted = real
                    event.save()

                    try:
                        discussion = SuggestedDiscussion.objects.get(
                            event=event,
                            enabled=True
                        )
                        real_discussion = Discussion.objects.create(
                            enabled=True,
                            event=real,
                            notify_all=discussion.notify_all,
                            moderate_all=discussion.moderate_all,
                        )
                        for moderator in discussion.moderators.all():
                            real_discussion.moderators.add(moderator)
                    except SuggestedDiscussion.DoesNotExist:
                        pass

                    # if this is a popcorn event, and there is a default
                    # popcorn template, then assign that
                    if real.popcorn_url:
                        real.status = Event.STATUS_SCHEDULED
                        templates = Template.objects.filter(
                            default_popcorn_template=True
                        )
                        for template in templates[:1]:
                            real.template = template
                        real.save()

                    sending.email_about_accepted_suggestion(
                        event,
                        real,
                        request
                    )
                    messages.info(
                        request,
                        'New event created from suggestion.'
                    )
                    if real.popcorn_url or not event.upcoming:
                        url = reverse('manage:events')
                    else:
                        url = reverse('manage:event_edit', args=(real.pk,))
                    return redirect(url)
                else:
                    print real_event_form.errors
    else:
        form = forms.AcceptSuggestedEventForm(instance=event)

    # we don't need the label for this form layout
    comment_form.fields['comment'].label = ''

    comments = (
        SuggestedEventComment.objects
        .filter(suggested_event=event)
        .select_related('User')
        .order_by('created')
    )

    discussion = None
    for each in SuggestedDiscussion.objects.filter(event=event):
        discussion = each

    context = {
        'event': event,
        'form': form,
        'real_event_form': real_event_form,
        'comment_form': comment_form,
        'comments': comments,
        'discussion': discussion,
    }
    return render(request, 'manage/suggestion_review.html', context)


@staff_required
@permission_required('main.change_event')
def tags(request):
    return render(request, 'manage/tags.html')


@staff_required
@permission_required('main.change_event')
@json_view
def tags_data(request):
    context = {}
    tags = []

    counts = {}
    qs = (
        Event.tags.through.objects.all()
        .values('tag_id').annotate(Count('tag'))
    )
    for each in qs:
        counts[each['tag_id']] = each['tag__count']

    _repeats = collections.defaultdict(int)
    for tag in Tag.objects.all():
        _repeats[tag.name.lower()] += 1

    for tag in Tag.objects.all():
        tags.append({
            'name': tag.name,
            'id': tag.id,
            '_usage_count': counts.get(tag.id, 0),
            '_repeated': _repeats[tag.name.lower()] > 1,
        })
    context['tags'] = tags
    context['urls'] = {
        'manage:tag_edit': reverse('manage:tag_edit', args=(0,)),
        'manage:tag_remove': reverse('manage:tag_remove', args=(0,)),
    }
    return context


@staff_required
@permission_required('main.change_event')
@cancel_redirect('manage:tags')
@transaction.commit_on_success
def tag_edit(request, id):
    tag = get_object_or_404(Tag, id=id)
    if request.method == 'POST':
        form = forms.TagEditForm(request.POST, instance=tag)
        if form.is_valid():
            tag = form.save()
            if Tag.objects.filter(name__iexact=tag.name).exclude(pk=tag.pk):
                messages.warning(
                    request,
                    "The tag you edited already exists with that same case "
                    "insensitive spelling."
                )
                return redirect('manage:tag_edit', tag.pk)
            else:
                edit_url = reverse('manage:tag_edit', args=(tag.pk,))
                messages.info(
                    request,
                    'Tag "%s" saved. [Edit again](%s)' % (tag, edit_url)
                )
                return redirect('manage:tags')
    else:
        form = forms.TagEditForm(instance=tag)
    repeated = Tag.objects.filter(name__iexact=tag.name).count()
    context = {
        'form': form,
        'tag': tag,
        'repeated': repeated,
        'is_repeated': repeated > 1
    }
    if repeated:
        context['repeated_form'] = forms.TagMergeForm(name=tag.name)
    return render(request, 'manage/tag_edit.html', context)


@staff_required
@permission_required('main.change_event')
@transaction.commit_on_success
def tag_remove(request, id):
    if request.method == 'POST':
        tag = get_object_or_404(Tag, id=id)
        for event in Event.objects.filter(tags=tag):
            event.tags.remove(tag)
        messages.info(request, 'Tag "%s" removed.' % tag.name)
        tag.delete()
    return redirect(reverse('manage:tags'))


@staff_required
@permission_required('main.change_event')
@cancel_redirect('manage:tags')
@transaction.commit_on_success
def tag_merge(request, id):
    tag = get_object_or_404(Tag, id=id)
    name_to_keep = request.POST['name']

    tag_to_keep = None
    for t in Tag.objects.filter(name__iexact=tag.name):
        if t.name == name_to_keep:
            tag_to_keep = t
            break

    merge_count = 0
    for t in Tag.objects.filter(name__iexact=tag.name):
        if t.name != name_to_keep:
            for event in Event.objects.filter(tags=t):
                event.tags.remove(t)
                event.tags.add(tag_to_keep)
            t.delete()
            merge_count += 1

    messages.info(
        request,
        'Merged ' +
        ('1 tag' if merge_count == 1 else '%d tag' % merge_count) +
        ' into "%s".' % tag_to_keep.name
    )

    return redirect('manage:tags')


@superuser_required
def vidly_media(request):
    data = {}
    events = Event.objects.filter(
        Q(template__name__contains='Vid.ly')
        |
        Q(pk__in=VidlySubmission.objects.all()
            .values_list('event_id', flat=True))
    )

    status = request.GET.get('status')
    if status:
        if status not in ('New', 'Processing', 'Finished', 'Error'):
            return http.HttpResponseBadRequest("Invalid 'status' value")

        # make a list of all tags -> events
        _tags = {}
        for event in events:
            environment = event.template_environment or {}
            if not environment.get('tag') or environment.get('tag') == 'None':
                continue
            _tags[environment['tag']] = event.id

        event_ids = []
        for tag in vidly.medialist(status):
            try:
                event_ids.append(_tags[tag])
            except KeyError:
                # it's on vid.ly but not in this database
                logging.debug("Unknown event with tag=%r", tag)

        events = events.filter(id__in=event_ids)

    events = events.order_by('-start_time')
    events = events.select_related('template')

    paged = paginate(events, request.GET.get('page'), 15)
    vidly_resubmit_form = forms.VidlyResubmitForm()
    data = {
        'paginate': paged,
        'status': status,
        'vidly_resubmit_form': vidly_resubmit_form,
    }
    return render(request, 'manage/vidly_media.html', data)


@superuser_required
@json_view
def vidly_media_status(request):
    if request.GET.get('tag'):
        tag = request.GET.get('tag')
    else:
        if not request.GET.get('id'):
            return http.HttpResponseBadRequest("No 'id'")
        event = get_object_or_404(Event, pk=request.GET['id'])
        environment = event.template_environment or {}

        if not environment.get('tag') or environment.get('tag') == 'None':
            # perhaps it has a VidlySubmission anyway
            submissions = (
                VidlySubmission.objects
                .exclude(tag__isnull=True)
                .filter(event=event).order_by('-submission_time')
            )
            for submission in submissions[:1]:
                environment = {'tag': submission.tag}
                break
            else:
                return {}
        tag = environment['tag']

    cache_key = 'vidly-query-{md5}'.format(
        md5=hashlib.md5(tag.encode('utf8')).hexdigest().strip())
    force = request.GET.get('refresh', False)
    if force:
        results = None  # force a refresh
    else:
        results = cache.get(cache_key)
    if not results:
        results = vidly.query(tag).get(tag, {})
        expires = 60
        # if it's healthy we might as well cache a bit
        # longer because this is potentially used a lot
        if results.get('Status') == 'Finished':
            expires = 60 * 60
        if results:
            cache.set(cache_key, results, expires)

    _status = results.get('Status')
    return {'status': _status}


@superuser_required
@json_view
def vidly_media_info(request):

    def as_fields(result):
        return [
            {'key': a, 'value': b}
            for (a, b)
            in sorted(result.items())
        ]

    if not request.GET.get('id'):
        return http.HttpResponseBadRequest("No 'id'")
    event = get_object_or_404(Event, pk=request.GET['id'])
    environment = event.template_environment or {}

    if not environment.get('tag') or environment.get('tag') == 'None':
        # perhaps it has a VidlySubmission anyway
        submissions = (
            VidlySubmission.objects
            .exclude(tag__isnull=True)
            .filter(event=event).order_by('-submission_time')
        )
        for submission in submissions[:1]:
            environment = {'tag': submission.tag}
            break

    if not environment.get('tag') or environment.get('tag') == 'None':
        return {'fields': as_fields({
            '*Note*': 'Not a valid tag in template',
            '*Template contents*': unicode(environment),
        })}
    else:
        tag = environment['tag']
        cache_key = 'vidly-query-%s' % tag
        force = request.GET.get('refresh', False)
        if force:
            results = None  # force a refresh
        else:
            results = cache.get(cache_key)
        if not results:
            all_results = vidly.query(tag)
            if tag not in all_results:
                return {
                    'ERRORS': ['Tag (%s) not found in Vid.ly' % tag]
                }
            results = all_results[tag]
            cache.set(cache_key, results, 60)

    data = {'fields': as_fields(results)}
    is_hd = results.get('IsHD', False)
    if is_hd == 'false':
        is_hd = False

    data['past_submission'] = {
        'url': results['SourceFile'],
        'email': results['UserEmail'],
        'hd': bool(is_hd),
        'token_protection': event.privacy != Event.PRIVACY_PUBLIC,
    }
    if request.GET.get('past_submission_info'):
        qs = (
            VidlySubmission.objects
            .filter(event=event)
            .order_by('-submission_time')
        )
        for submission in qs[:1]:
            if event.privacy != Event.PRIVACY_PUBLIC:
                # forced
                token_protection = True
            else:
                # whatever it was before
                token_protection = submission.token_protection
            data['past_submission'] = {
                'url': submission.url,
                'email': submission.email,
                'hd': submission.hd,
                'token_protection': token_protection,
            }

    return data


@require_POST
@superuser_required
def vidly_media_resubmit(request):
    if request.POST.get('cancel'):
        return redirect(reverse('manage:vidly_media') + '?status=Error')

    form = forms.VidlyResubmitForm(data=request.POST)
    if not form.is_valid():
        return http.HttpResponse(str(form.errors))
    event = get_object_or_404(Event, pk=form.cleaned_data['id'])
    environment = event.template_environment or {}
    if not environment.get('tag') or environment.get('tag') == 'None':
        raise ValueError("Not a valid tag in template")

    if event.privacy != Event.PRIVACY_PUBLIC:
        token_protection = True  # no choice
    else:
        token_protection = form.cleaned_data['token_protection']

    old_tag = environment['tag']
    shortcode, error = vidly.add_media(
        url=form.cleaned_data['url'],
        email=form.cleaned_data['email'],
        hd=form.cleaned_data['hd'],
        token_protection=token_protection
    )
    VidlySubmission.objects.create(
        event=event,
        url=form.cleaned_data['url'],
        email=form.cleaned_data['email'],
        token_protection=token_protection,
        hd=form.cleaned_data['hd'],
        tag=shortcode,
        submission_error=error
    )

    if error:
        messages.warning(
            request,
            "Media could not be re-submitted:\n<br>\n%s" % error
        )
    else:
        messages.success(
            request,
            "Event re-submitted to use tag '%s'" % shortcode
        )
        vidly.delete_media(
            old_tag,
            email=form.cleaned_data['email']
        )
        event.template_environment['tag'] = shortcode
        event.save()

        cache_key = 'vidly-query-%s' % old_tag
        cache.delete(cache_key)

    return redirect(reverse('manage:vidly_media') + '?status=Error')


@staff_required
@permission_required('main.change_urlmatch')
def url_transforms(request):
    data = {}

    matchers = []
    for matcher in URLMatch.objects.order_by('-modified'):
        matchers.append((
            matcher,
            URLTransform.objects.filter(match=matcher).order_by('order')
        ))
    data['matchers'] = matchers

    available_variables = []
    url_transform_passwords = settings.URL_TRANSFORM_PASSWORDS
    for key in sorted(url_transform_passwords):
        available_variables.append("{{ password('%s') }}" % key)
    data['available_variables'] = available_variables

    return render(request, 'manage/url_transforms.html', data)


@staff_required
@permission_required('main.change_urlmatch')
@transaction.commit_on_success
def url_match_new(request):
    if request.method == 'POST':
        form = forms.URLMatchForm(data=request.POST)
        if form.is_valid():
            form.save()
            messages.info(request, 'New match added.')
            return redirect('manage:url_transforms')
    else:
        form = forms.URLMatchForm()
    return render(request, 'manage/url_match_new.html', {'form': form})


@staff_required
@permission_required('main.change_urlmatch')
@transaction.commit_on_success
@require_POST
def url_match_remove(request, id):
    url_match = get_object_or_404(URLMatch, id=id)
    name = url_match.name
    for transform in URLTransform.objects.filter(match=url_match):
        transform.delete()
    url_match.delete()

    messages.info(request, "URL Match '%s' removed." % name)
    return redirect('manage:url_transforms')


@staff_required
@json_view
def url_match_run(request):
    url = request.GET['url']
    result, error = url_transformer.run(url, dry=True)
    return {'result': result, 'error': error}


@staff_required
@permission_required('main.change_urlmatch')
@transaction.commit_on_success
@require_POST
@json_view
def url_transform_add(request, id):
    match = get_object_or_404(URLMatch, id=id)
    find = request.POST['find']
    replace_with = request.POST['replace_with']
    next_order = (
        URLTransform.objects
        .filter(match=match)
        .aggregate(Max('order'))
    )
    if next_order['order__max'] is None:
        next_order = 1
    else:
        next_order = next_order['order__max'] + 1
    transform = URLTransform.objects.create(
        match=match,
        find=find,
        replace_with=replace_with,
        order=next_order,
    )
    transform_as_dict = {
        'id': transform.id,
        'find': transform.find,
        'replace_with': transform.replace_with,
        'order': transform.order,
    }
    return {'transform': transform_as_dict}


@staff_required
@permission_required('main.change_urlmatch')
@transaction.commit_on_success
@require_POST
@json_view
def url_transform_remove(request, id, transform_id):
    match = get_object_or_404(URLMatch, id=id)
    transform = get_object_or_404(URLTransform, id=transform_id, match=match)
    transform.delete()
    return True


@staff_required
@permission_required('main.change_urlmatch')
@transaction.commit_on_success
@require_POST
@json_view
def url_transform_edit(request, id, transform_id):
    match = get_object_or_404(URLMatch, id=id)
    transform = get_object_or_404(URLTransform, id=transform_id, match=match)
    transform.find = request.POST['find']
    transform.replace_with = request.POST['replace_with']
    transform.save()
    return True


def cron_pings(request):  # pragma: no cover
    """reveals if the cron_ping management command has recently been fired
    by the cron jobs."""
    if 'LocMemCache' in cache.__class__.__name__:
        return http.HttpResponse(
            "Using LocMemCache so can't test this",
            content_type='text/plain'
        )
    ping = cache.get('cron-ping')
    if not ping:
        return http.HttpResponse(
            'cron-ping has not been executed for at least an hour',
            content_type='text/plain'
        )
    now = datetime.datetime.utcnow()
    return http.HttpResponse(
        'Last cron-ping: %s\n'
        '           Now: %s' % (ping, now),
        content_type='text/plain'
    )


@staff_required
@permission_required('main.add_event')
def event_hit_stats(request):

    possible_order_by = ('total_hits', 'hits_per_day', 'score')
    order_by = request.GET.get('order')
    if order_by not in possible_order_by:
        order_by = possible_order_by[-1]

    include_excluded = bool(request.GET.get('include_excluded'))
    today = datetime.datetime.utcnow().replace(tzinfo=utc)
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
@transaction.commit_on_success
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
                Q(user__email__icontains=form.cleaned_data['user'])
                |
                Q(user__first_name__icontains=form.cleaned_data['user'])
                |
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


@staff_required
@permission_required('comments.change_comment')
@transaction.commit_on_success
def comment_edit(request, id):
    context = {}
    comment = get_object_or_404(Comment, id=id)
    if request.method == 'POST':
        if request.POST.get('cancel'):
            return redirect('manage:event_comments', comment.event.pk)

        form = forms.CommentEditForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                'Comment changes saved.'
            )
            return redirect('manage:comment_edit', comment.pk)
    else:
        form = forms.CommentEditForm(instance=comment)
    context['comment'] = comment
    context['event'] = comment.event
    context['form'] = form
    return render(request, 'manage/comment_edit.html', context)


@staff_required
@permission_required('comments.change_discussion')
@transaction.commit_on_success
def all_comments(request):
    context = {}

    comments = Comment.objects.all().select_related('user', 'event')
    form = forms.CommentsFilterForm(request.GET)
    filtered = False
    if form.is_valid():
        if form.cleaned_data['event']:
            comments = comments.filter(
                event__title__icontains=form.cleaned_data['event']
            )
        if form.cleaned_data['status'] == 'flagged':
            comments = comments.filter(flagged__gt=0)
            filtered = True
        elif form.cleaned_data['status']:
            comments = comments.filter(status=form.cleaned_data['status'])
            filtered = True
        if form.cleaned_data['user']:
            user_filter = (
                Q(user__email__icontains=form.cleaned_data['user'])
                |
                Q(user__first_name__icontains=form.cleaned_data['user'])
                |
                Q(user__last_name__icontains=form.cleaned_data['user'])
            )
            comments = comments.filter(user_filter)
            filtered = True
        if form.cleaned_data['comment']:
            comments = comments.filter(
                comment__icontains=form.cleaned_data['comment']
            )
            filtered = True

    comments = comments.order_by('-created')
    context['count'] = comments.count()
    paged = paginate(comments, request.GET.get('page'), 20)
    context['paginate'] = paged
    context['form'] = form
    context['filtered'] = filtered
    return render(request, 'manage/comments.html', context)


@permission_required('main.change_event')
@json_view
def curated_groups_autocomplete(request):
    q = request.GET.get('q', '').strip()
    if not q:
        return {'groups': []}

    all = mozillians.get_all_groups_cached()

    def describe_group(group):
        if group['number_of_members'] == 1:
            return '%s (1 member)' % (group['name'],)
        else:
            return (
                '%s (%s members)' % (group['name'], group['number_of_members'])
            )

    groups = [
        (x['name'], describe_group(x))
        for x in all
        if q.lower() in x['name'].lower()
    ]
    return {'groups': groups}


def insufficient_permissions(request):
    context = {}
    perm = request.session.get('failed_permission')
    if perm:
        # convert that into the actual Permission object
        ct, codename = perm.split('.', 1)
        try:
            permission = Permission.objects.get(
                content_type__app_label=ct,
                codename=codename
            )
            context['failed_permission'] = permission
        except Permission.DoesNotExist:
            warnings.warn('Unable to find permission %r' % perm)
    return render(request, 'manage/insufficient_permissions.html', context)


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
    now = datetime.datetime.utcnow().replace(tzinfo=utc)
    qs = Event.objects.filter(start_time__gte=now)
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

    now = datetime.datetime.utcnow().replace(tzinfo=utc)
    base_qs = EventAssignment.objects.all().order_by('-event__start_time')
    if assignee:
        base_qs = base_qs.filter(users=assignee)

    title = 'Airmo'
    if assignee:
        title += ' for %s' % assignee.email
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
    base_url = '%s://%s' % (
        request.is_secure() and 'https' or 'http',
        RequestSite(request).domain
    )
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
            event.start_time + datetime.timedelta(hours=1)
        )
        vevent.add('description').value = unhtml(short_desc(event))
        vevent.add('url').value = (
            base_url + reverse('main:event', args=(event.slug,))
        )
    icalstream = cal.serialize()
    # response = http.HttpResponse(icalstream,
    #                          mimetype='text/plain; charset=utf-8')
    response = http.HttpResponse(icalstream,
                                 mimetype='text/calendar; charset=utf-8')
    filename = 'AirMozillaEventAssignments'
    filename += '.ics'
    response['Content-Disposition'] = (
        'inline; filename=%s' % filename)
    cache.set(cache_key, response, 60 * 10)  # 10 minutes

    # https://bugzilla.mozilla.org/show_bug.cgi?id=909516
    response['Access-Control-Allow-Origin'] = '*'

    return response


@staff_required
@permission_required('main.change_recruitmentmessage')
def recruitmentmessages(request):
    context = {}
    context['recruitmentmessages'] = RecruitmentMessage.objects.all()

    def count_events(this):
        return Event.objects.filter(recruitmentmessage=this).count()

    context['count_events'] = count_events
    return render(request, 'manage/recruitmentmessages.html', context)


@staff_required
@permission_required('main.add_recruitmentmessage')
@cancel_redirect('manage:recruitmentmessages')
@transaction.commit_on_success
def recruitmentmessage_new(request):
    if request.method == 'POST':
        form = forms.RecruitmentMessageEditForm(
            request.POST,
            instance=RecruitmentMessage()
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Recruitment message created.')
            return redirect('manage:recruitmentmessages')
    else:
        form = forms.RecruitmentMessageEditForm()
    context = {'form': form}
    return render(request, 'manage/recruitmentmessage_new.html', context)


@staff_required
@permission_required('main.change_recruitmentmessage')
@cancel_redirect('manage:recruitmentmessages')
@transaction.commit_on_success
def recruitmentmessage_edit(request, id):
    msg = RecruitmentMessage.objects.get(id=id)
    if request.method == 'POST':
        form = forms.RecruitmentMessageEditForm(request.POST, instance=msg)
        if form.is_valid():
            msg = form.save()
            messages.info(request, 'Recruitment message saved.')
            return redirect('manage:recruitmentmessages')
    else:
        form = forms.RecruitmentMessageEditForm(instance=msg)
    context = {
        'form': form,
        'recruitmentmessage': msg,
        'events_using': (
            Event.objects.filter(recruitmentmessage=msg).order_by('title')
        )
    }
    return render(request, 'manage/recruitmentmessage_edit.html', context)


@staff_required
@permission_required('main.delete_recruitmentmessage')
@transaction.commit_on_success
def recruitmentmessage_delete(request, id):
    if request.method == 'POST':
        msg = RecruitmentMessage.objects.get(id=id)
        msg.delete()
        messages.info(request, 'Recruitment message deleted.')
    return redirect('manage:recruitmentmessages')


@staff_required
@permission_required('main.change_event')
@cancel_redirect(lambda r, id: reverse('manage:event_edit', args=(id,)))
@transaction.commit_on_success
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


@staff_required
@permission_required('surveys.change_survey')
@transaction.commit_on_success
def surveys_(request):  # funny name to avoid clash with surveys module
    context = {
        'surveys': Survey.objects.all().order_by('-created'),
    }

    def count_events(this):
        return Survey.events.through.objects.filter(survey=this).count()

    def count_survey_questions(this):
        return Question.objects.filter(survey=this).count()

    context['count_events'] = count_events
    context['count_survey_questions'] = count_survey_questions
    return render(request, 'manage/surveys.html', context)


@staff_required
@permission_required('surveys.change_survey')
@transaction.commit_on_success
def survey_new(request):
    if request.method == 'POST':
        form = forms.SurveyNewForm(
            request.POST,
            instance=Survey()
        )
        if form.is_valid():
            survey = form.save()
            messages.success(request, 'Survey created.')
            return redirect('manage:survey_edit', survey.id)
    else:
        form = forms.SurveyNewForm()
    context = {'form': form}
    return render(request, 'manage/survey_new.html', context)


@staff_required
@permission_required('surveys.change_survey')
@cancel_redirect('manage:surveys')
@transaction.commit_on_success
def survey_edit(request, id):
    survey = get_object_or_404(Survey, id=id)
    if request.method == 'POST':
        form = forms.SurveyEditForm(request.POST, instance=survey)
        if form.is_valid():
            form.save()
            messages.info(request, 'Survey saved.')
            return redirect('manage:surveys')
    else:
        form = forms.SurveyEditForm(instance=survey)
    context = {
        'form': form,
        'survey': survey,
        'events_using': Event.objects.filter(survey=survey),
        'questions': Question.objects.filter(survey=survey),
    }
    return render(request, 'manage/survey_edit.html', context)


@require_POST
@staff_required
@permission_required('surveys.delete_survey')
@cancel_redirect('manage:surveys')
@transaction.commit_on_success
def survey_delete(request, id):
    survey = get_object_or_404(Survey, id=id)
    survey.delete()
    return redirect('manage:surveys')


@require_POST
@staff_required
@permission_required('surveys.add_question')
@transaction.commit_on_success
def survey_question_new(request, id):
    survey = get_object_or_404(Survey, id=id)
    Question.objects.create(survey=survey)
    return redirect('manage:survey_edit', survey.id)


@json_view
@require_POST
@staff_required
@permission_required('surveys.change_question')
@transaction.commit_on_success
def survey_question_edit(request, id, question_id):
    survey = get_object_or_404(Survey, id=id)
    question = get_object_or_404(Question, survey=survey, id=question_id)

    if 'question' in request.POST:
        # it must be valid JSON
        form = forms.QuestionForm(request.POST)
        if form.is_valid():
            question.question = form.cleaned_data['question']
            question.save()
        else:
            return {'error': form.errors['question']}
    elif request.POST.get('ordering') in ('up', 'down'):
        direction = request.POST.get('ordering')
        questions = list(Question.objects.filter(survey=survey))
        current = questions.index(question)
        this = questions.pop(current)
        if direction == 'up':
            questions.insert(current - 1, this)
        else:
            questions.insert(current + 1, this)

        for i, question in enumerate(questions):
            if i != question.order:
                question.order = i
                question.save()

        return redirect('manage:survey_edit', survey.id)
    else:  # pragma: no cover
        raise NotImplementedError

    return {
        'question': json.dumps(question.question, indent=2)
    }


@require_POST
@staff_required
@permission_required('surveys.delete_question')
@transaction.commit_on_success
def survey_question_delete(request, id, question_id):
    survey = get_object_or_404(Survey, id=id)
    get_object_or_404(Question, survey=survey, id=question_id).delete()
    return redirect('manage:survey_edit', survey.id)


@superuser_required
def loggedsearches(request):
    searches = (
        LoggedSearch.objects
        .select_related('event_clicked')
        .order_by('-date')
    )
    paged = paginate(searches, request.GET.get('page'), 20)
    context = {
        'paginate': paged,
        'hash_user_id': lambda x: str(hash(str(x)))[-4:],
    }

    return render(request, 'manage/loggedsearches.html', context)


@superuser_required
def loggedsearches_stats(request):
    context = {}

    now = datetime.datetime.utcnow().replace(tzinfo=utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    this_week = today - datetime.timedelta(days=today.weekday())
    this_month = today.replace(day=1)
    this_year = this_month.replace(month=1)

    groups = (
        ('All searches', {}),
        ('Successful searches', {'results__gt': 0}),
        ('Failed searches', {'results': 0}),
    )
    context['groups'] = []
    qs_base = LoggedSearch.objects.all()
    for group_name, filters in groups:
        qs = qs_base.filter(**filters)

        counts = {}
        counts['today'] = qs.filter(date__gte=today).count()
        counts['this_week'] = qs.filter(date__gte=this_week).count()
        counts['this_month'] = qs.filter(date__gte=this_month).count()
        counts['this_year'] = qs.filter(date__gte=this_year).count()
        counts['ever'] = qs.count()
        context['groups'].append((group_name, counts, False))

    qs = (
        qs_base.extra(
            select={'term_lower': 'LOWER(term)'}
        )
        .values('term_lower')
        .annotate(count=Count('term'))
        .order_by('-count')
    )
    terms = {}
    terms['today'] = qs.filter(date__gte=today)[:5]
    terms['this_week'] = qs.filter(date__gte=this_week)[:5]
    terms['this_month'] = qs.filter(date__gte=this_month)[:5]
    terms['this_year'] = qs.filter(date__gte=this_year)[:5]
    terms['ever'] = qs[:5]
    context['groups'].append(
        (
            'Most common terms (case insensitive, top 5)',
            terms,
            True
        )
    )

    return render(request, 'manage/loggedsearches_stats.html', context)


@staff_required
def picturegallery(request):
    context = {}
    if request.GET.get('event'):
        event = get_object_or_404(Event, id=request.GET.get('event'))
        result = can_edit_event(
            event,
            request.user,
            default='manage:picturegallery'
        )
        if isinstance(result, http.HttpResponse):
            return result

        context['event'] = event

    return render(request, 'manage/picturegallery.html', context)


@staff_required
@json_view
def picturegallery_data(request):
    context = {}
    if request.GET.get('event'):
        event = get_object_or_404(Event, id=request.GET['event'])
    else:
        event = None

    cache_key = '_get_all_pictures'
    if event:
        cache_key += str(event.id)
    items = cache.get(cache_key)

    if items is None:
        items = _get_all_pictures(event=event)
        # this is invalidated in models.py
        cache.set(cache_key, items, 60)

    context['pictures'] = items
    context['urls'] = {
        'manage:picture_edit': reverse('manage:picture_edit', args=('0',)),
        'manage:picture_delete': reverse('manage:picture_delete', args=('0',)),
        'manage:redirect_picture_thumbnail': reverse(
            'manage:redirect_picture_thumbnail', args=('0',)
        ),
        'manage:picture_event_associate': reverse(
            'manage:picture_event_associate', args=('0',)
        ),
        'manage:event_edit': reverse('manage:event_edit', args=('0',)),
    }
    context['stats'] = {
        'total_pictures': Picture.objects.all().count(),
        'event_pictures': Picture.objects.filter(event__isnull=False).count(),
    }

    return context


def _get_all_pictures(event=None):

    values = (
        'id',
        'title',
        'placeholder_img',
        'picture_id'
    )
    event_map = collections.defaultdict(list)
    cant_delete = collections.defaultdict(bool)
    for each in Event.objects.filter(picture__isnull=False).values(*values):
        event_map[each['picture_id']].append({
            'id': each['id'],
            'title': each['title']
        })
        if not each['placeholder_img']:
            # then you can definitely not delete this picture
            cant_delete[each['picture_id']] = True

    pictures = []
    values = (
        'id',
        'size',
        'width',
        'height',
        'notes',
        'created',
        'modified',
        'modified_user',
    )
    qs = Picture.objects.all()
    if event:
        qs = qs.filter(
            Q(event__isnull=True) |
            Q(event=event)
        )
    else:
        qs = qs.filter(event__isnull=True)
    for picture_dict in qs.order_by('event', '-created').values(*values):
        picture = dot_dict(picture_dict)
        item = {
            'id': picture.id,
            'width': picture.width,
            'height': picture.height,
            'size': picture.size,
            'created': picture.created.isoformat(),
            'events': event_map[picture.id]
        }
        if cant_delete.get(picture.id):
            item['cant_delete'] = True
        if picture.notes:
            item['notes'] = picture.notes
        # if picture.id in event_map:
        #     item['events'] = event_map[picture.id]
        pictures.append(item)
    return pictures


@staff_required
@permission_required('main.change_picture')
@transaction.commit_on_success
def picture_edit(request, id):
    picture = get_object_or_404(Picture, id=id)
    context = {'picture': picture}

    if request.method == 'POST':
        form = forms.PictureForm(request.POST, request.FILES, instance=picture)
        if form.is_valid():
            picture = form.save()
            return redirect('manage:picturegallery')
    else:
        form = forms.PictureForm(instance=picture)
    context['form'] = form
    return render(request, 'manage/picture_edit.html', context)


@staff_required
@permission_required('main.delete_picture')
@transaction.commit_on_success
@json_view
def picture_delete(request, id):
    picture = get_object_or_404(Picture, id=id)
    for event in Event.objects.filter(picture=picture):
        if not event.placeholder_img:
            return http.HttpResponseBadRequest("Can't delete this")
    picture.delete()
    return True


@staff_required
@permission_required('main.add_picture')
@transaction.commit_on_success
@json_view
def picture_add(request):
    context = {}
    if request.GET.get('event'):
        event = get_object_or_404(Event, id=request.GET.get('event'))
        result = can_edit_event(
            event,
            request.user,
            default='manage:picturegallery'
        )
        if isinstance(result, http.HttpResponse):
            return result

        context['event'] = event
    if request.method == 'POST':
        if request.POST.get('remove'):
            # this is for when you change your mind
            size = request.POST['size']
            filename = request.POST['name']
            notes = filename_to_notes(filename)
            matches = Picture.objects.filter(
                notes=notes,
                size=int(size),
                modified_user=request.user
            )
            for picture in matches.order_by('-created')[:1]:
                picture.delete()
                return True
            return False

        form = forms.PictureForm(request.POST, request.FILES)
        if form.is_valid():
            picture = form.save(commit=False)
            picture.modified_user = request.user
            picture.save()
            return redirect('manage:picturegallery')
    else:
        form = forms.PictureForm()
    context['form'] = form
    return render(request, 'manage/picture_add.html', context)


@cache_page(60)
def redirect_picture_thumbnail(request, id):
    picture = get_object_or_404(Picture, id=id)
    geometry = request.GET.get('geometry', '100x100')
    crop = request.GET.get('crop', 'center')
    thumb = thumbnail(picture.file, geometry, crop=crop)
    return redirect(thumb.url)


@staff_required
@require_POST
@transaction.commit_on_success
@permission_required('main.change_event')
@json_view
def picture_event_associate(request, id):
    picture = get_object_or_404(Picture, id=id)
    if not request.POST.get('event'):
        return http.HttpResponseBadRequest("Missing 'event'")
    event = get_object_or_404(Event, id=request.POST['event'])
    event.picture = picture
    event.save()
    return True


@superuser_required
def cronlogger_home(request):
    return render(request, 'manage/cronlogger.html')


@superuser_required
@json_view
def cronlogger_data(request):
    context = {}
    values = (
        'job',
        'created',
        'stdout',
        'stderr',
        'exc_type',
        'exc_value',
        'exc_traceback',
        'duration',
    )
    qs = CronLog.objects.all()
    jobs = []
    for each in qs.values('job').annotate(Count('job')):
        jobs.append({
            'text': '%s (%d)' % (each['job'], each['job__count']),
            'value': each['job']
        })
    jobs.sort(key=lambda x: x['value'])
    context['jobs'] = jobs

    if request.GET.get('job'):
        qs = qs.filter(job__exact=request.GET['job'])
    context['count'] = qs.count()
    logs = []
    for log_dict in qs.order_by('-created').values(*values)[:100]:
        log = dot_dict(log_dict)
        log['created'] = log['created'].isoformat()
        logs.append(log)
    context['logs'] = logs

    return context
