import collections
import datetime
import hashlib
import functools
import logging
import re
import uuid
import urlparse

from django.conf import settings
from django import http
from django.contrib.auth.decorators import (permission_required,
                                            user_passes_test)
from django.contrib.auth.models import User, Group
from django.core.cache import cache
from django.contrib import messages
from django.core.mail import EmailMessage
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.contrib.flatpages.models import FlatPage
from django.utils.timezone import utc
from django.contrib.sites.models import RequestSite

import pytz
from funfactory.urlresolvers import reverse
from jinja2 import Environment, meta

from airmozilla.main.helpers import short_desc
from airmozilla.base.utils import (
    json_view,
    paginate,
    tz_apply,
    html_to_text,
    unhtml
)
from airmozilla.main.models import (
    Approval,
    Category,
    Event,
    EventTweet,
    Location,
    Participant,
    Tag,
    Template,
    Channel,
    SuggestedEvent,
    VidlySubmission
)
from airmozilla.manage import forms
from airmozilla.manage.tweeter import send_tweet
from airmozilla.manage import vidly


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


def cancel_redirect(redirect_view):
    """Redirect wrapper for POST requests which contain a cancel field."""
    def inner_render(fn):
        @functools.wraps(fn)
        def wrapped(request, *args, **kwargs):
            if request.method == 'POST' and 'cancel' in request.POST:
                return redirect(reverse(redirect_view))
            return fn(request, *args, **kwargs)
        return wrapped
    return inner_render


@staff_required
def dashboard(request):
    """Management home / explanation page."""
    admin_email_addresses = []
    for user in User.objects.filter(is_superuser=True).exclude(email=''):
        if user.email not in admin_email_addresses:
            admin_email_addresses.append(user.email)
    if not admin_email_addresses:
        admin_email_addresses = [x[1] for x in settings.ADMINS]
    return render(request, 'manage/dashboard.html',
                  {'admin_email_addresses': admin_email_addresses})


@staff_required
@permission_required('auth.change_user')
def users(request):
    """User editor:  view users and update a user's group."""
    if request.method == 'POST':
        form = forms.UserFindForm(request.POST)
        if form.is_valid():
            user = User.objects.get(email=form.cleaned_data['email'])
            return redirect('manage:user_edit', user.id)
    else:
        form = forms.UserFindForm()
    users_paged = paginate(User.objects.all(), request.GET.get('page'), 10)

    _mozilla_email_filter = (
        Q(email__endswith='@mozillafoundation.org') |
        Q(email__endswith='@mozilla.com')
    )
    users_stats = {
        'total': User.objects.all().count(),
        'total_mozilla_email': (
            User.objects.filter(_mozilla_email_filter).count()
        ),
    }
    return render(request, 'manage/users.html',
                  {'paginate': users_paged,
                   'form': form,
                   'users_stats': users_stats})


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
    tz = pytz.timezone(request.POST['timezone'])
    event.start_time = tz_apply(event.start_time, tz)
    if event.archive_time:
        event.archive_time = tz_apply(event.archive_time, tz)
    if 'approvals' in form.cleaned_data:
        event.save()
        approvals_old = [app.group for app in event.approval_set.all()]
        approvals_new = form.cleaned_data['approvals']
        approvals_add = set(approvals_new).difference(approvals_old)
        approvals_remove = set(approvals_old).difference(approvals_new)
        for approval in approvals_add:
            group = Group.objects.get(name=approval)
            app = Approval(group=group, event=event)
            app.save()
            emails = [u.email for u in group.user_set.filter(is_active=True)]
            if not emails:
                continue
            subject = ('[Air Mozilla] Approval requested: "%s"' %
                       event.title)
            message = render_to_string(
                'manage/_email_approval.html',
                {
                    'group': group.name,
                    'manage_url': request.build_absolute_uri(
                        reverse('manage:approvals')
                    ),
                    'title': event.title,
                    'creator': event.creator.email,
                    'datetime': event.start_time,
                    'description': html_to_text(event.description),
                }
            )
            email = EmailMessage(subject, message,
                                 settings.EMAIL_FROM_ADDRESS, emails)
            email.send()
        for approval in approvals_remove:
            app = Approval.objects.get(group=approval, event=event)
            app.delete()


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
    if duplicate_id:
        # Use a blank event, but fill in the initial data from duplication_id
        event_initial = Event.objects.get(id=duplicate_id)
        # We copy the initial data from a form generated on the origin event
        # to retain initial data processing, e.g., on EnvironmentField.
        event_initial_form = form_class(instance=event_initial)
        for field in event_initial_form.fields:
            if field in event_initial_form.initial:
                # Usual initial form data
                initial[field] = event_initial_form.initial[field]
            else:
                # Populated by form __init__ (e.g., approvals)
                initial[field] = event_initial_form.fields[field].initial
        # Excluded fields in an event copy
        blank_fields = ('slug', 'start_time')
        for field in blank_fields:
            initial[field] = ''

    if request.method == 'POST':
        event = Event()
        if duplicate_id and 'placeholder_img' not in request.FILES:
            # If this is a duplicate event action and a placeholder_img
            # was not provided, copy it from the duplication source.
            event.placeholder_img = event_initial.placeholder_img
        form = form_class(request.POST, request.FILES, instance=event)
        if form.is_valid():
            event = form.save(commit=False)
            _event_process(request, form, event)
            event.save()
            form.save_m2m()
            messages.success(request,
                             'Event "%s" created.' % event.title)
            return redirect('manage:events')
    else:
        form = form_class(initial=initial)
    return render(request, 'manage/event_request.html', {'form': form,
                  'duplicate_event': event_initial})


@staff_required
@permission_required('main.change_event')
def events(request):
    """Event edit/production:  approve, change, and publish events."""
    if request.user.has_perm('main.change_event_others'):
        creator_filter = {}
    else:
        creator_filter = {'creator': request.user}
    search_results = []
    if request.method == 'POST':
        search_form = forms.EventFindForm(request.POST)
        if search_form.is_valid():
            search_results = Event.objects.filter(
                title__icontains=search_form.cleaned_data['title'],
                **creator_filter
            ).order_by('-start_time')
    else:
        search_form = forms.EventFindForm()
    initiated = (Event.objects.initiated().filter(**creator_filter)
                 .order_by('start_time')
                 .select_related('category', 'location'))
    upcoming = (Event.objects.upcoming().filter(**creator_filter)
                .order_by('start_time').select_related('category', 'location'))
    live = (Event.objects.live().filter(**creator_filter)
            .order_by('start_time').select_related('category', 'location'))
    archiving = (Event.objects.archiving().filter(**creator_filter)
                 .order_by('-archive_time')
                 .select_related('category', 'location'))
    archived = (Event.objects.archived_and_removed().filter(**creator_filter)
                .order_by('-start_time')
                .select_related('category', 'location'))
    archived_paged = paginate(archived, request.GET.get('page'), 10)
    return render(request, 'manage/events.html', {
        'initiated': initiated,
        'upcoming': upcoming,
        'live': live,
        'archiving': archiving,
        'archived': archived_paged,
        'form': search_form,
        'search_results': search_results
    })


@staff_required
@permission_required('main.change_event')
@cancel_redirect('manage:events')
@transaction.commit_on_success
def event_edit(request, id):
    """Edit form for a particular event."""
    event = get_object_or_404(Event, id=id)
    if (not request.user.has_perm('main.change_event_others') and
            request.user != event.creator):
        return redirect('manage:events')
    if request.user.has_perm('main.change_event_others'):
        form_class = forms.EventEditForm
    elif request.user.has_perm('main.add_event_scheduled'):
        form_class = forms.EventExperiencedRequestForm
    else:
        form_class = forms.EventRequestForm

    if request.method == 'POST':
        form = form_class(request.POST, request.FILES, instance=event)
        if form.is_valid():
            event = form.save(commit=False)
            _event_process(request, form, event)
            event.save()
            form.save_m2m()
            messages.info(request, 'Event "%s" saved.' % event.title)
            return redirect('manage:events')
    else:
        timezone.activate(pytz.timezone('UTC'))
        form = form_class(instance=event, initial={
            'timezone': timezone.get_current_timezone()  # UTC
        })
    data = {
        'form': form,
        'event': event,
        'suggested_event': None,
        'tweets': EventTweet.objects.filter(event=event).order_by('id'),
    }
    try:
        suggested_event = SuggestedEvent.objects.get(accepted=event)
        data['suggested_event'] = suggested_event
    except SuggestedEvent.DoesNotExist:
        pass

    data['is_vidly_event'] = False
    if event.template and 'Vid.ly' in event.template.name:
        data['is_vidly_event'] = True
        data['vidly_submissions'] = (
            VidlySubmission.objects
            .filter(event=event)
            .order_by('-submission_time')
        )
    return render(request, 'manage/event_edit.html', data)


@superuser_required
def event_vidly_submissions(request, id):
    event = get_object_or_404(Event, id=id)
    submissions = (
        VidlySubmission.objects
        .filter(event=event)
        .order_by('submission_time')
    )
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
        'submission_time': submission.submission_time,
    }
    if request.GET.get('as_fields'):
        return {'fields': as_fields(data)}
    return data


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
@permission_required('main.add_event')
@json_view
def tag_autocomplete(request):
    """Feeds JSON tag names to the Event request/edit form."""
    query = request.GET['q']
    tags = Tag.objects.filter(name__istartswith=query)[:5]
    tag_names = [{'id': t.name, 'text': t.name} for t in tags]
    # for new tags - the first tag is the query
    tag_names.insert(0, {'id': query, 'text': query})
    return {'tags': tag_names}


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
            minutes = form.cleaned_data['archive_time']
            now = (datetime.datetime.utcnow()
                   .replace(tzinfo=utc, microsecond=0))
            event.archive_time = (
                now + datetime.timedelta(minutes=minutes)
            )
            event.save()
            messages.info(request, 'Event "%s" saved.' % event.title)
            return redirect('manage:events')
    else:
        form = forms.EventArchiveForm(instance=event)
    vidly_shortcut_form = forms.VidlyURLForm(
        initial=dict(email=request.user.email)
    )
    return render(request, 'manage/event_archive.html',
                  {'form': form,
                   'event': event,
                   'vidly_shortcut_form': vidly_shortcut_form})


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
        email = EmailMessage(subject, message, from_addr, [to_addr],
                             cc=cc, headers={'Reply-To': reply_to})
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
@permission_required('main.change_category')
def categories(request):
    categories = Category.objects.all()
    return render(request, 'manage/categories.html',
                  {'categories': categories})


@staff_required
@permission_required('main.add_category')
@cancel_redirect('manage:categories')
@transaction.commit_on_success
def category_new(request):
    if request.method == 'POST':
        form = forms.CategoryForm(request.POST, instance=Category())
        if form.is_valid():
            form.save()
            messages.success(request, 'Category created.')
            return redirect('manage:categories')
    else:
        form = forms.CategoryForm()
    return render(request, 'manage/category_new.html', {'form': form})


@staff_required
@permission_required('main.change_category')
@cancel_redirect('manage:categories')
@transaction.commit_on_success
def category_edit(request, id):
    category = Category.objects.get(id=id)
    if request.method == 'POST':
        form = forms.CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.info(request, 'Category "%s" saved.' % category.name)
            return redirect('manage:categories')
    else:
        form = forms.CategoryForm(instance=category)
    return render(request, 'manage/category_edit.html',
                  {'form': form, 'category': category})


@staff_required
@permission_required('main.delete_category')
@transaction.commit_on_success
def category_remove(request, id):
    if request.method == 'POST':
        category = Category.objects.get(id=id)
        category.delete()
        messages.info(request, 'Category "%s" removed.' % category.name)
    return redirect('manage:categories')


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
            form.save()
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


@staff_required
@permission_required('main.change_template')
@json_view
def template_env_autofill(request):
    """JSON response containing undefined variables in the requested template.
       Provides template for filling in environment."""
    template_id = request.GET['template']
    template = Template.objects.get(id=template_id)
    env = Environment()
    ast = env.parse(template.content)

    exceptions = ('vidly_tokenize', 'edgecast_tokenize')
    undeclared_variables = [x for x in meta.find_undeclared_variables(ast)
                            if x not in exceptions]
    var_templates = ["%s=" % v for v in undeclared_variables]
    return {'variables':  '\n'.join(var_templates)}


@staff_required
@permission_required('main.change_template')
def templates(request):
    data = {}
    data['templates'] = Template.objects.all()

    def count_events_with_template(template):
        return Event.objects.filter(template=template).count()

    data['count_events_with_template'] = count_events_with_template
    return render(request, 'manage/templates.html', data)


@staff_required
@permission_required('main.change_template')
@cancel_redirect('manage:templates')
@transaction.commit_on_success
def template_edit(request, id):
    template = Template.objects.get(id=id)
    if request.method == 'POST':
        form = forms.TemplateEditForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
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
    locations = Location.objects.all()
    return render(request, 'manage/locations.html', {'locations': locations})


@staff_required
@permission_required('main.change_location')
@cancel_redirect('manage:locations')
@transaction.commit_on_success
def location_edit(request, id):
    location = Location.objects.get(id=id)
    if request.method == 'POST':
        form = forms.LocationEditForm(request.POST, instance=location)
        if form.is_valid():
            form.save()
            messages.info(request, 'Location "%s" saved.' % location)
            return redirect('manage:locations')
    else:
        form = forms.LocationEditForm(instance=location)
    return render(request, 'manage/location_edit.html', {'form': form,
                                                         'location': location})


@staff_required
@permission_required('main.add_location')
@cancel_redirect('manage:home')
@transaction.commit_on_success
def location_new(request):
    if request.method == 'POST':
        form = forms.LocationEditForm(request.POST, instance=Location())
        if form.is_valid():
            form.save()
            messages.success(request, 'Location created.')
            if request.user.has_perm('main.change_location'):
                return redirect('manage:locations')
            else:
                return redirect('manage:home')
    else:
        form = forms.LocationEditForm()
    return render(request, 'manage/location_new.html', {'form': form})


@staff_required
@permission_required('main.delete_location')
@transaction.commit_on_success
def location_remove(request, id):
    if request.method == 'POST':
        location = Location.objects.get(id=id)
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
        )
    else:
        approvals = recent = Approval.objects.none()
    data = {
        'approvals': approvals,
        'recent': recent,
        'user_groups': groups,
    }
    return render(request, 'manage/approvals.html', data)


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
    return render(request, 'manage/approval_review.html',
                  {'approval': approval, 'form': form})


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
        if shortcode:
            return {'shortcode': shortcode}
        else:
            return http.HttpResponseBadRequest(error)
    return http.HttpResponseBadRequest(str(form.errors))


@staff_required
@permission_required('main.add_event')
def suggestions(request):
    data = {}
    events = (
        SuggestedEvent.objects
        .filter(accepted=None)
        .exclude(submitted=None)
        .order_by('submitted')
    )
    data['events'] = events
    return render(request, 'manage/suggestions.html', data)


@staff_required
@permission_required('main.add_event')
@transaction.commit_on_success
def suggestion_review(request, id):
    event = get_object_or_404(SuggestedEvent, pk=id)
    real_event_form = None
    if request.method == 'POST':
        form = forms.AcceptSuggestedEventForm(
            request.POST,
            instance=event,
        )
        reject = request.POST.get('reject')
        if reject:
            form.fields['review_comments'].required = True

        if form.is_valid():
            form.save()
            if reject:
                event.submitted = None
                event.save()
                _email_about_rejected_suggestion(event, request)
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
                    'creator': event.user.pk,
                    'start_time': event.start_time,
                    'timezone': event.location.timezone,
                    'location': event.location.pk,
                    'category': event.category and event.category.pk or None,
                    'channels': [x.pk for x in event.channels.all()],
                    'call_info': event.call_info,
                    #'additional_links': event.additional_links,
                    'privacy': event.privacy,
                }
                real_event_form = forms.EventRequestForm(
                    data=dict_event,
                )
                real_event_form.fields['placeholder_img'].required = False
                if real_event_form.is_valid():
                    real = real_event_form.save(commit=False)
                    real.placeholder_img = event.placeholder_img

                    real.slug = event.slug
                    real.additional_links = event.additional_links
                    real.remote_presenters = event.remote_presenters
                    real.save()
                    [real.tags.add(x) for x in event.tags.all()]
                    [real.channels.add(x) for x in event.channels.all()]
                    event.accepted = real
                    event.save()
                    _email_about_accepted_suggestion(event, real, request)
                    messages.info(
                        request,
                        'New event created from suggestion.'
                    )
                    url = reverse('manage:event_edit', args=(real.pk,))
                    return redirect(url)
                else:
                    print real_event_form.errors
    else:
        form = forms.AcceptSuggestedEventForm(instance=event)
    data = {
        'event': event,
        'form': form,
        'real_event_form': real_event_form,
    }
    return render(request, 'manage/suggestion_review.html', data)


def _email_about_accepted_suggestion(event, real, request):
    emails = (event.user.email,)
    subject = (
        '[Air Mozilla] Suggested event accepted!'
    )
    base_url = (
        '%s://%s' % (request.is_secure() and 'https' or 'http',
                     RequestSite(request).domain)
    )
    message = render_to_string(
        'manage/_email_suggested_accepted.html',
        {
            'event': event,
            'base_url': base_url,
            'request': request,
        }
    )
    email = EmailMessage(
        subject,
        message,
        settings.EMAIL_FROM_ADDRESS,
        emails
    )
    email.send()


def _email_about_rejected_suggestion(event, request):
    emails = (event.user.email,)
    subject = (
        '[Air Mozilla] Suggested event not accepted'
    )
    base_url = (
        '%s://%s' % (request.is_secure() and 'https' or 'http',
                     RequestSite(request).domain)
    )
    message = render_to_string(
        'manage/_email_suggested_rejected.html',
        {
            'event': event,
            'base_url': base_url,
            'request': request,
        }
    )
    email = EmailMessage(
        subject,
        message,
        settings.EMAIL_FROM_ADDRESS,
        emails
    )
    email.send()


@staff_required
@permission_required('main.change_event')
def tags(request):
    if request.GET.get('clear'):
        return redirect(reverse('manage:tags'))
    tags = Tag.objects.all()
    search = request.GET.get('search', '').strip()
    if search:
        tags = tags.filter(name__icontains=search)
    paged = paginate(tags, request.GET.get('page'), 10)
    data = {
        'paginate': paged,
        'search': search,
    }
    return render(request, 'manage/tags.html', data)


@staff_required
@permission_required('main.change_event')
@cancel_redirect('manage:tags')
@transaction.commit_on_success
def tag_edit(request, id):
    tag = get_object_or_404(Tag, id=id)
    if request.method == 'POST':
        form = forms.TagEditForm(request.POST, instance=tag)
        if form.is_valid():
            form.save()
            messages.info(request, 'Tag "%s" saved.' % tag)
            return redirect('manage:tags')
    else:
        form = forms.TagEditForm(instance=tag)
    return render(request, 'manage/tag_edit.html', {'form': form,
                                                    'tag': tag})


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


@superuser_required
def vidly_media(request):
    data = {}
    events = Event.objects.filter(
        template__name__contains='Vid.ly'
    )
    status = request.GET.get('status')
    if status:
        if status not in ('New', 'Processing', 'Finished', 'Error'):
            return http.HttpResponseBadRequest("Invalid 'status' value")

        # make a list of all tags -> events
        _tags = {}
        for event in events:
            environment = event.template_environment
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
    if not request.GET.get('id'):
        return http.HttpResponseBadRequest("No 'id'")
    event = get_object_or_404(Event, pk=request.GET['id'])
    environment = event.template_environment
    if not environment.get('tag') or environment.get('tag') == 'None':
        return {}
    tag = environment['tag']
    cache_key = 'vidly-query-%s' % tag
    force = request.GET.get('refresh', False)
    if force:
        results = None  # force a refresh
    else:
        results = cache.get(cache_key)
    if not results:
        results = vidly.query(tag)[tag]
        expires = 60
        # if it's healthy we might as well cache a bit
        # longer because this is potentially used a lot
        if results.get('Status') == 'Finished':
            expires = 60 * 60
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
    environment = event.template_environment
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
            results = vidly.query(tag)[tag]
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
            data['past_submission'] = {
                'url': submission.url,
                'email': submission.email,
                'hd': submission.hd,
                'token_protection': submission.token_protection,
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
    environment = event.template_environment
    if not environment.get('tag') or environment.get('tag') == 'None':
        raise ValueError("Not a valid tag in template")

    old_tag = environment['tag']
    shortcode, error = vidly.add_media(
        url=form.cleaned_data['url'],
        email=form.cleaned_data['email'],
        hd=form.cleaned_data['hd'],
        token_protection=form.cleaned_data['token_protection']
    )
    VidlySubmission.objects.create(
        event=event,
        url=form.cleaned_data['url'],
        email=form.cleaned_data['email'],
        token_protection=form.cleaned_data['token_protection'],
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
