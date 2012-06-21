import re

from django.contrib.auth.decorators import permission_required, \
                                           user_passes_test
from django.contrib.auth.models import User, Group
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse
from django.shortcuts import render, redirect

from airmozilla.base.utils import json_view
from airmozilla.main.models import Category, Event, Participant, Tag
from airmozilla.manage.forms import CategoryForm, GroupEditForm, \
                                    EventRequestForm, ParticipantEditForm, \
                                    ParticipantFindForm, UserEditForm, \
                                    UserFindForm

staff_required = user_passes_test(lambda u: u.is_staff)


@staff_required
def home(request):
    """Management homepage / explanation page."""
    return render(request, 'manage/home.html')


@staff_required
@permission_required('change_user')
def users(request):
    """User editor:  view users and update a user's group."""
    if request.method == 'POST':
        form = UserFindForm(request.POST)
        if form.is_valid():
            user = User.objects.get(email=form.cleaned_data['email'])
            return redirect('manage:user_edit', user.id)
    else:
        form = UserFindForm()
    users = User.objects.all()
    paginator = Paginator(users, 10)
    page = request.GET.get('page')
    try:
        users_paged = paginator.page(page)
    except PageNotAnInteger:
        users_paged = paginator.page(1)
    except EmptyPage:
        users_paged = paginator.page(paginator.num_pages)
    return render(request, 'manage/users.html',
                  {'paginate': users_paged, 'form': form})


@staff_required
@permission_required('change_user')
def user_edit(request, id):
    """Editing an individual user."""
    user = User.objects.get(id=id)
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('manage:users')
    else:
        form = UserEditForm(instance=user)
    return render(request, 'manage/user_edit.html', {'form': form, 'u': user})


@staff_required
@permission_required('change_group')
def groups(request):
    """Group editor: view groups and change group permissions."""
    groups = Group.objects.all()
    return render(request, 'manage/groups.html', {'groups': groups})


@staff_required
@permission_required('change_group')
def group_edit(request, id):
    """Edit an individual group."""
    group = Group.objects.get(id=id)
    if request.method == 'POST':
        form = GroupEditForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            return redirect('manage:groups')
    else:
        form = GroupEditForm(instance=group)
    return render(request, 'manage/group_edit.html',
                  {'form': form, 'g': group})


@staff_required
@permission_required('add_group')
def group_new(request):
    """Add a new group."""
    group = Group()
    if request.method == 'POST':
        form = GroupEditForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            return redirect('manage:groups')
    else:
        form = GroupEditForm(instance=group)
    return render(request, 'manage/group_new.html', {'form': form})


@staff_required
@permission_required('add_event')
def event_request(request):
    """Event request page:  create new events to be published."""
    if request.method == 'POST':
        form = EventRequestForm(request.POST, request.FILES, instance=Event())
        if form.is_valid():
            form.save()
            return redirect('manage:home')
    else:
        form = EventRequestForm()
    return render(request, 'manage/event_request.html', {'form': form})


@staff_required
@permission_required('add_event')
@json_view
def tag_autocomplete(request):
    """ Feeds JSON tag names to the Event Request form. """
    query = request.GET['q']
    tags = Tag.objects.filter(name__istartswith=query)[:5]
    tag_names = [{'id': t.name, 'text': t.name} for t in tags]
    # for new tags - the first tag is the query
    tag_names.insert(0, {'id': query, 'text': query})
    return {'tags': tag_names}


@staff_required
@permission_required('add_event')
@json_view
def participant_autocomplete(request):
    """ Participant names to Event Request autocompleter. """
    query = request.GET['q']
    participants = Participant.objects.filter(name__icontains=query)
    # Only match names with a component which starts with the query
    regex = re.compile(r'\b%s' % re.escape(query.split()[0]), re.I)
    participant_names = [{'id': p.name, 'text': p.name} 
                         for p in participants if regex.findall(p.name)]
    return {'participants': participant_names[:5]}


@staff_required
@permission_required('change_participant')
def participants(request):
    """Participants page:  view and search participants/speakers. """
    if request.method == 'POST':
        search_form = ParticipantFindForm(request.POST)
        if search_form.is_valid():
            participants = Participant.objects.filter(name__icontains=
                                       search_form.cleaned_data['name'])
        else:
            participants = Participant.objects.all()
    else:
        participants = Participant.objects.all()
        search_form = ParticipantFindForm()
    paginator = Paginator(participants, 10)
    page = request.GET.get('page')
    try:
        participants_paged = paginator.page(page)
    except PageNotAnInteger:
        participants_paged = paginator.page(1)
    except EmptyPage:
        participants_paged = paginator.page(paginator.num_pages)
    return render(request, 'manage/participants.html',
                  {'paginate': participants_paged, 'form': search_form})


@staff_required
@permission_required('changed_participant')
def participant_edit(request, id):
    """ Participant edit page:  update biographical info. """
    participant = Participant.objects.get(id=id)
    if request.method == 'POST':
        form = ParticipantEditForm(request.POST, request.FILES,
                                   instance=participant)
        if form.is_valid():
            form.save()
            return redirect('manage:participants')
    else:
        form = ParticipantEditForm(instance=participant)
    return render(request, 'manage/participant_edit.html',
                  {'form': form, 'participant': participant})


@staff_required
@permission_required('add_participant')
def participant_new(request):
    if request.method == 'POST':
        form = ParticipantEditForm(request.POST, request.FILES,
                                   instance=Participant())
        if form.is_valid():
            form.save()
            return redirect('manage:participants')
    else:
        form = ParticipantEditForm()
    return render(request, 'manage/participant_new.html',
                  {'form': form})


@staff_required
@permission_required('change_event')
def event_edit(request):
    """Event edit/production:  change, approve, publish events."""
    return render(request, 'manage/event_edit.html')


@staff_required
@permission_required('change_category')
def categories(request):
    categories = Category.objects.all()
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=Category())
        if form.is_valid():
            form.save()
            form = CategoryForm()
    else:
        form = CategoryForm()
    return render(request, 'manage/categories.html',
                  {'categories': categories, 'form': form})
