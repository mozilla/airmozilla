from django.contrib.auth.decorators import permission_required, \
                                           user_passes_test
from django.contrib.auth.models import User, Group
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils import simplejson

from airmozilla.main.models import Category, Event, Tag
from airmozilla.manage.forms import CategoryForm, GroupEditForm, \
                                    EventRequestForm, UserEditForm, \
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
    return render(request, 'manage/users.html',
                  {'users': users_paged, 'form': form})


@staff_required
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
            return redirect('manage.groups')
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
            return redirect('manage.groups')
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
            return redirect('manage.home')
    else:
        form = EventRequestForm()
    return render(request, 'manage/event_request.html', {'form': form})


@staff_required
@permission_required('add_event')
def tag_autocomplete(request):
    """ Feeds JSON tag names to the Event Request form. """
    query = request.GET['q']
    tags = Tag.objects.filter(name__istartswith=query)[:5]
    tag_names = [{'id': t.name, 'text': t.name} for t in tags]
    # for new tags - the first tag is the query
    tag_names.insert(0, {'id': query, 'text': query})
    result = {'tags': tag_names}
    return HttpResponse(simplejson.dumps(result), mimetype='application/json')


@staff_required
@permission_required('change_participant')
def participant_edit(request):
    """Participant editor page:  update biographical info."""
    return render(request, 'manage/participant_edit.html')


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
