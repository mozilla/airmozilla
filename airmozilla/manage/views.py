import datetime
import functools
import pytz
import re
import uuid

from django.conf import settings
from django.contrib.auth.decorators import (permission_required,
                                            user_passes_test)
from django.contrib.auth.models import User, Group
from django.core.mail import EmailMessage
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.utils import timezone

from funfactory.urlresolvers import reverse
from jinja2 import Environment, meta

from airmozilla.base.utils import json_view, paginate, tz_apply
from airmozilla.main.models import (Approval, Category, Event, EventOldSlug,
                                    Location, Participant, Tag, Template)
from airmozilla.manage import forms


staff_required = user_passes_test(lambda u: u.is_staff)


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
    return render(request, 'manage/dashboard.html')


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
    return render(request, 'manage/users.html',
                  {'paginate': users_paged, 'form': form})


@staff_required
@permission_required('auth.change_user')
@cancel_redirect('manage:users')
def user_edit(request, id):
    """Editing an individual user."""
    user = User.objects.get(id=id)
    if request.method == 'POST':
        form = forms.UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
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
def group_edit(request, id):
    """Edit an individual group."""
    group = Group.objects.get(id=id)
    if request.method == 'POST':
        form = forms.GroupEditForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            return redirect('manage:groups')
    else:
        form = forms.GroupEditForm(instance=group)
    return render(request, 'manage/group_edit.html',
                  {'form': form, 'group': group})


@staff_required
@permission_required('auth.add_group')
def group_new(request):
    """Add a new group."""
    group = Group()
    if request.method == 'POST':
        form = forms.GroupEditForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            return redirect('manage:groups')
    else:
        form = forms.GroupEditForm(instance=group)
    return render(request, 'manage/group_new.html', {'form': form})


@staff_required
@permission_required('auth.delete_group')
def group_remove(request, id):
    if request.method == 'POST':
        group = Group.objects.get(id=id)
        group.delete()
    return redirect('manage:groups')


@staff_required
@permission_required('main.add_event')
@cancel_redirect('manage:events')
def event_request(request):
    """Event request page:  create new events to be published."""
    if request.user.has_perm('main.add_event_scheduled'):
        form_class = forms.EventExperiencedRequestForm
    else:
        form_class = forms.EventRequestForm
    if request.method == 'POST':
        form = form_class(request.POST, request.FILES,
                          instance=Event())
        if form.is_valid():
            event = form.save(commit=False)
            tz = pytz.timezone(request.POST['timezone'])
            event.start_time = tz_apply(event.start_time, tz)
            if event.archive_time:
                event.archive_time = tz_apply(event.archive_time, tz)
            event.creator = request.user
            event.modified_user = request.user
            event.save()
            form.save_m2m()
            return redirect('manage:events')
    else:
        form = form_class()
    return render(request, 'manage/event_request.html', {'form': form})


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
                 .order_by('start_time'))
    upcoming = (Event.objects.upcoming().filter(**creator_filter)
                .order_by('start_time'))
    live = (Event.objects.live().filter(**creator_filter)
            .order_by('start_time'))
    archiving = (Event.objects.archiving().filter(**creator_filter)
                 .order_by('-archive_time'))
    archived = (Event.objects.archived().filter(**creator_filter)
                .order_by('-archive_time'))
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
def event_edit(request, id):
    """Edit form for a particular event."""
    event = Event.objects.get(id=id)
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
            tz = pytz.timezone(request.POST['timezone'])
            event.start_time = tz_apply(event.start_time, tz)
            if event.archive_time:
                event.archive_time = tz_apply(event.archive_time, tz)
            if 'approvals' in form.cleaned_data:
                approvals_old = [app.group for app in event.approval_set.all()]
                approvals_new = form.cleaned_data['approvals']
                approvals_add = set(approvals_new).difference(approvals_old)
                approvals_remove = set(approvals_old).difference(approvals_new)
                for approval in approvals_add:
                    group = Group.objects.get(name=approval)
                    app = Approval(group=group, event=event)
                    app.save()
                    emails = [u.email for u in group.user_set.all()]
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
                            'description': event.description
                        }
                    )
                    email = EmailMessage(subject, message,
                                         settings.EMAIL_FROM_ADDRESS, emails)
                    email.send()
                for approval in approvals_remove:
                    app = Approval.objects.get(group=approval, event=event)
                    app.delete()
            event.modified_user = request.user
            event.save()
            form.save_m2m()
            return redirect('manage:events')
    else:
        timezone.activate(pytz.timezone('UTC'))
        tag_format = lambda objects: ','.join(map(unicode, objects))
        participants_formatted = tag_format(event.participants.all())
        tags_formatted = tag_format(event.tags.all())
        form = form_class(instance=event, initial={
            'participants': participants_formatted,
            'tags': tags_formatted,
            'timezone': timezone.get_current_timezone()  # UTC
        })
    return render(request, 'manage/event_edit.html', {'form': form,
                                                      'event': event})


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
def event_archive(request, id):
    """Dedicated page for setting page template (archive) and archive time."""
    event = Event.objects.get(id=id)
    if request.method == 'POST':
        form = forms.EventArchiveForm(request.POST, instance=event)
        if form.is_valid():
            event = form.save(commit=False)
            minutes = form.cleaned_data['archive_time']
            event.archive_time = (
                event.start_time + datetime.timedelta(minutes=minutes)
            )
            event.save()
            return redirect('manage:events')
    else:
        form = forms.EventArchiveForm(instance=event)

    return render(request, 'manage/event_archive.html',
                  {'form': form, 'event': event})


@staff_required
@permission_required('main.delete_event')
def event_remove(request, id):
    if request.method == 'POST':
        event = Event.objects.get(id=id)
        slugs = EventOldSlug.objects.filter(event=event)
        for slug in slugs:
            slug.delete()
        event.delete()
    return redirect('manage:events')


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
            if 'sendmail' in request.POST:
                return redirect('manage:participant_email', id=participant.id)
            return redirect('manage:participants')
    else:
        form = forms.ParticipantEditForm(instance=participant)
    return render(request, 'manage/participant_edit.html',
                  {'form': form, 'participant': participant})


@staff_required
@permission_required('main.delete_participant')
def participant_remove(request, id):
    if request.method == 'POST':
        participant = Participant.objects.get(id=id)
        participant.delete()
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
def participant_new(request):
    if request.method == 'POST':
        form = forms.ParticipantEditForm(request.POST, request.FILES,
                                         instance=Participant())
        if form.is_valid():
            participant = form.save(commit=False)
            participant.creator = request.user
            participant.save()
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
def category_new(request):
    if request.method == 'POST':
        form = forms.CategoryForm(request.POST, instance=Category())
        if form.is_valid():
            form.save()
            return redirect('manage:categories')
    else:
        form = forms.CategoryForm()
    return render(request, 'manage/category_new.html', {'form': form})


@staff_required
@permission_required('main.change_category')
@cancel_redirect('manage:categories')
def category_edit(request, id):
    category = Category.objects.get(id=id)
    if request.method == 'POST':
        form = forms.CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            return redirect('manage:categories')
    else:
        form = forms.CategoryForm(instance=category)
    return render(request, 'manage/category_edit.html',
                  {'form': form, 'category': category})


@staff_required
@permission_required('main.delete_category')
def category_remove(request, id):
    if request.method == 'POST':
        category = Category.objects.get(id=id)
        category.delete()
    return redirect('manage:categories')


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
    undeclared_variables = list(meta.find_undeclared_variables(ast))
    var_templates = ["%s=" % v for v in undeclared_variables]
    return {'variables':  '\n'.join(var_templates)}


@staff_required
@permission_required('main.change_template')
def templates(request):
    templates = Template.objects.all()
    return render(request, 'manage/templates.html', {'templates': templates})


@staff_required
@permission_required('main.change_template')
@cancel_redirect('manage:templates')
def template_edit(request, id):
    template = Template.objects.get(id=id)
    if request.method == 'POST':
        form = forms.TemplateEditForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            return redirect('manage:templates')
    else:
        form = forms.TemplateEditForm(instance=template)
    return render(request, 'manage/template_edit.html', {'form': form,
                                                         'template': template})


@staff_required
@permission_required('main.add_template')
@cancel_redirect('manage:templates')
def template_new(request):
    if request.method == 'POST':
        form = forms.TemplateEditForm(request.POST, instance=Template())
        if form.is_valid():
            form.save()
            return redirect('manage:templates')
    else:
        form = forms.TemplateEditForm()
    return render(request, 'manage/template_new.html', {'form': form})


@staff_required
@permission_required('main.delete_template')
def template_remove(request, id):
    if request.method == 'POST':
        template = Template.objects.get(id=id)
        template.delete()
    return redirect('manage:templates')


@staff_required
@permission_required('main.change_location')
def locations(request):
    locations = Location.objects.all()
    return render(request, 'manage/locations.html', {'locations': locations})


@staff_required
@permission_required('main.change_location')
@cancel_redirect('manage:locations')
def location_edit(request, id):
    location = Location.objects.get(id=id)
    if request.method == 'POST':
        form = forms.LocationEditForm(request.POST, instance=location)
        if form.is_valid():
            form.save()
            return redirect('manage:locations')
    else:
        form = forms.LocationEditForm(instance=location)
    return render(request, 'manage/location_edit.html', {'form': form,
                                                         'location': location})


@staff_required
@permission_required('main.add_location')
@cancel_redirect('manage:home')
def location_new(request):
    if request.method == 'POST':
        form = forms.LocationEditForm(request.POST, instance=Location())
        if form.is_valid():
            form.save()
            if request.user.has_perm('main.change_location'):
                return redirect('manage:locations')
            else:
                return redirect('manage:home')
    else:
        form = forms.LocationEditForm()
    return render(request, 'manage/location_new.html', {'form': form})


@staff_required
@permission_required('main.delete_location')
def location_remove(request, id):
    if request.method == 'POST':
        location = Location.objects.get(id=id)
        location.delete()
    return redirect('manage:locations')


@staff_required
@json_view
def location_timezone(request):
    """Responds with the timezone for the requested Location.  Used to
       auto-fill the timezone form in event requests/edits."""
    location = get_object_or_404(Location, id=request.GET['location'])
    return {'timezone': location.timezone}


@staff_required
@permission_required('main.change_approval')
def approvals(request):
    user = request.user
    approvals = Approval.objects.filter(group__in=user.groups.all(),
                                        processed=False)
    recent = (Approval.objects.filter(group__in=user.groups.all(),
                                      processed=True)
                      .order_by('-processed_time')[:25])
    return render(request, 'manage/approvals.html', {'approvals': approvals,
                                                     'recent': recent})


@staff_required
@permission_required('main.change_approval')
def approval_review(request, id):
    """Approve/deny an event on behalf of a group."""
    approval = Approval.objects.get(id=id)
    if approval.group not in request.user.groups.all():
        return redirect('manage:approvals')
    if request.method == 'POST':
        form = forms.ApprovalForm(request.POST, instance=approval)
        approval = form.save(commit=False)
        approval.approved = 'approve' in request.POST
        approval.processed = True
        approval.user = request.user
        approval.save()
        return redirect('manage:approvals')
    else:
        form = forms.ApprovalForm(instance=approval)
    return render(request, 'manage/approval_review.html',
                  {'approval': approval, 'form': form})
