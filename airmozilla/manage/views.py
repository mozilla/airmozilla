from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import User, Group
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect

from airmozilla.manage.forms import UserEditForm, GroupEditForm, UserFindForm


@staff_member_required
def home(request):
    """Management homepage / explanation page."""
    return render(request, 'home.html')


@staff_member_required
@permission_required('change_user')
def users(request):
    """User editor:  view users and update a user's group."""
    if request.method == 'POST':
        form = UserFindForm(request.POST)
        if form.is_valid():
            user = User.objects.get(email=form.cleaned_data['email'])
            return redirect('manage.user_edit', user.id)
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
    return render(request, 'users.html', {'users': users_paged, 'form': form})


@staff_member_required
@permission_required('change_user')
def user_edit(request, id):
    """Editing an individual user."""
    user = User.objects.get(id=id)
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('manage.users')
    else:
        form = UserEditForm(instance=user)
    return render(request, 'user_edit.html', {'form': form, 'u': user})


@staff_member_required
@permission_required('change_group')
def groups(request):
    """Group editor: view groups and change group permissions."""
    groups = Group.objects.all()
    return render(request, 'groups.html', {'groups': groups})


@staff_member_required
@permission_required('change_group')
def group_edit(request, id):
    """Edit an individual group."""
    group = Group.objects.get(id=id)
    if request.method == 'POST':
        form = GroupEditForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            return redirect('manage.groups')
    else:
        form = GroupEditForm(instance=group)
    return render(request, 'group_edit.html', {'form': form, 'g': group})


@staff_member_required
@permission_required('add_group')
def group_new(request):
    """Add a new group."""
    group = Group()
    if request.method == 'POST':
        form = GroupEditForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            return redirect('manage.groups')
    else:
        form = GroupEditForm(instance=group)
    return render(request, 'group_new.html', {'form': form})


@staff_member_required
@permission_required('manage.event_request')
def event_request(request):
    """Event request page:  create new events to be published."""
    return render(request, 'event_request.html')


@staff_member_required
@permission_required('manage.participant_edit')
def participant_edit(request):
    """Participant editor page:  update biographical info."""
    return render(request, 'participant_edit.html')


@staff_member_required
@permission_required('manage.produce_events')
def event_edit(request):
    """Event edit/production:  change, approve, publish events."""
    return render(request, 'event_edit.html')
