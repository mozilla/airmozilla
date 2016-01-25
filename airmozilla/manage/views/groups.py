from django.contrib.auth.models import Group
from django.contrib import messages
from django.shortcuts import render, redirect
from django.db import transaction

from jsonview.decorators import json_view

from airmozilla.base import mozillians
from airmozilla.manage import forms

from .decorators import (
    staff_required,
    permission_required,
    cancel_redirect
)


@staff_required
@permission_required('auth.change_group')
def groups(request):
    """Group editor: view groups and change group permissions."""
    groups = Group.objects.all()
    return render(request, 'manage/groups.html', {'groups': groups})


@staff_required
@permission_required('auth.change_group')
@cancel_redirect('manage:groups')
@transaction.atomic
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
@transaction.atomic
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
@transaction.atomic
def group_remove(request, id):
    if request.method == 'POST':
        group = Group.objects.get(id=id)
        group.delete()
        messages.info(request, 'Group "%s" removed.' % group.name)
    return redirect('manage:groups')


@permission_required('main.change_event')
@json_view
def curated_groups_autocomplete(request):
    q = request.GET.get('q', '').strip()
    if not q:
        return {'groups': []}

    all = mozillians.get_all_groups_cached()

    def describe_group(group):
        if group['member_count'] == 1:
            return '%s (1 member)' % (group['name'],)
        else:
            return (
                '%s (%s members)' % (group['name'], group['member_count'])
            )

    groups = [
        (x['name'], describe_group(x))
        for x in all
        if q.lower() in x['name'].lower()
    ]
    # naively sort by how good the match is
    groups.sort(key=lambda x: x[0].lower().find(q.lower()))
    return {'groups': groups}
