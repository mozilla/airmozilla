import collections

from django import http
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.cache import cache
from django.contrib import auth
from django.contrib import messages
from django.shortcuts import render, redirect
from django.db import transaction
from django.db.models import Q
from django.core.urlresolvers import reverse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404

from jsonview.decorators import json_view

from airmozilla.main.models import UserProfile, UserEmailAlias
from airmozilla.manage import forms
from airmozilla.authentication import auth0

from .decorators import (
    staff_required,
    superuser_required,
    permission_required,
    cancel_redirect
)


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
    context = {
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
        'first_name',
        'last_name',
        'id',
        'last_login',
        'is_staff',
        'is_active',
        'is_superuser'
    )
    # make a big fat list of the user IDs of people who are contributors
    contributor_ids = (
        UserProfile.objects
        .filter(contributor=True)
        .values_list('user_id', flat=True)
    )
    all_users_with_id_token = set(
        UserProfile.objects.filter(
            id_token__isnull=False
        ).values_list('user_id', flat=True)
    )
    aliases = {}
    for alias in UserEmailAlias.objects.all().only('email', 'user__email'):
        if alias.user.email not in aliases:
            aliases[alias.user.email] = []
        aliases[alias.user.email].append(alias.email)

    for user in qs.only(*values).order_by('-last_login'):
        item = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
        if user.last_login:
            item['last_login'] = user.last_login.isoformat()
        # The reason we only add these if they're true is because we want
        # to minimize the amount of JSON we return. It works because in
        # javascript, doing `if (thing.something)` works equally if it
        # exists and is false or if it does not exist.
        if user.is_staff:
            item['is_staff'] = True
        if user.is_superuser:
            item['is_superuser'] = True
        if user.id in contributor_ids:
            item['is_contributor'] = True
        if not user.is_active:
            item['is_inactive'] = True
        if groups_map[user.id]:
            item['groups'] = groups_map[user.id]
        if user.id in all_users_with_id_token:
            item['has_id_token'] = True
        if user.email in aliases:
            item['aliases'] = aliases[user.email]

        users.append(item)
    return users


@staff_required
@permission_required('auth.change_user')
@cancel_redirect('manage:users')
@transaction.atomic
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
                  {'form': form, 'user_': user})


@staff_required
@permission_required('auth.change_user')
@json_view
def id_token_check(request):
    user_id = request.GET.get('id')
    if not user_id:
        return http.HttpResponseBadRequest('missing id')
    user = get_object_or_404(User, id=user_id)
    id_token = auth0.renew_id_token(user.profile.id_token)
    if id_token:
        user.profile.id_token = id_token
        user.profile.save()
        return {'valid': True}
    else:
        return {'valid': False}


@superuser_required
@require_POST
def signinas(request):
    assert request.user.is_superuser
    if not (request.POST.get('id') and request.POST.get('email')):
        return http.HttpResponseBadRequest('missing id and email')
    user = User.objects.get(
        id=request.POST['id'],
        email=request.POST['email']
    )
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    request.user = user
    auth.login(request, user)
    return redirect('/')
