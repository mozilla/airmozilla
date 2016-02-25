import calendar

from django.contrib.auth.models import User
from django import http
from django.shortcuts import get_object_or_404, render, redirect
from django.views.decorators.cache import cache_page
from django.template.loader import render_to_string
from django.db.models import Q, Max
from django.core.cache import cache
from django.db import transaction

from jsonview.decorators import json_view

from airmozilla.main.models import Event
from .models import Comment, Discussion, Unsubscription
from airmozilla.base.mozillians import fetch_user_name
from . import forms
from . import sending


def get_latest_comment(event, include_posted=False):
    latest_comment = Comment.objects
    if isinstance(event, int):
        latest_comment = latest_comment.filter(event_id=event)
    else:
        latest_comment = latest_comment.filter(event=event)

    if not include_posted:
        latest_comment = (
            latest_comment
            .filter(Q(status=Comment.STATUS_REMOVED) |
                    Q(status=Comment.STATUS_APPROVED))
        )

    latest_comment = latest_comment.aggregate(Max('modified'))
    if latest_comment:
        latest_comment = latest_comment['modified__max']
        if latest_comment:
            return calendar.timegm(latest_comment.utctimetuple())


def can_manage_comments(user, discussion):
    """return true if this user can do administrative things to the
    comments such as moderating them.
    """
    if user.is_authenticated():
        if user.is_superuser:
            return True
        elif discussion.moderators.filter(id=user.id).exists():
            return True
    return False


@json_view
@transaction.atomic
def event_data(request, id):
    event = get_object_or_404(Event, pk=id)
    context = {}
    try:
        discussion = Discussion.objects.get(event=event)
        context['discussion'] = {
            'enabled': discussion.enabled,
            'moderate_all': discussion.moderate_all,
            'closed': discussion.closed,
        }
    except Discussion.DoesNotExist:
        context['discussion'] = {
            'enabled': False
        }

    if not context['discussion']['enabled']:
        if request.method == 'POST':
            return http.HttpResponseBadRequest("Discussion not enabled")
        else:
            return context

    _can_manage_comments = can_manage_comments(request.user, discussion)

    if request.method == 'POST':

        if not request.user.is_authenticated():
            return http.HttpResponseForbidden(
                'Must be signed in'
            )

        if request.POST.get('approve'):
            # but are you allowed?
            if not _can_manage_comments:
                return http.HttpResponseForbidden(
                    'Unable to approve comment'
                )
            comment = get_object_or_404(Comment, pk=request.POST['approve'])
            comment.status = Comment.STATUS_APPROVED
            comment.save()
            if comment.reply_to:
                sending.send_reply_notification(comment, request)
            return {'ok': True}

        if request.POST.get('unapprove'):
            # but are you allowed?
            if not _can_manage_comments:
                return http.HttpResponseForbidden(
                    'Unable to unapprove comment'
                )
            comment = get_object_or_404(Comment, pk=request.POST['unapprove'])
            comment.status = Comment.STATUS_POSTED
            comment.save()
            return {'ok': True}

        if request.POST.get('remove'):
            # but are you allowed?
            if not _can_manage_comments:
                return http.HttpResponseForbidden(
                    'Unable to remove comment'
                )
            comment = get_object_or_404(Comment, pk=request.POST['remove'])
            comment.status = Comment.STATUS_REMOVED
            comment.save()
            return {'ok': True}

        if request.POST.get('flag'):
            comment = get_object_or_404(Comment, pk=request.POST['flag'])
            comment.flagged += 1
            comment.save()
            return {'ok': True}

        if request.POST.get('unflag'):
            # but are you allowed?
            if not _can_manage_comments:
                return http.HttpResponseForbidden(
                    'Unable to unflag comment'
                )
            comment = get_object_or_404(Comment, pk=request.POST['unflag'])
            comment.flagged = 0
            comment.save()
            return {'ok': True}

        form = forms.CommentForm(request.POST)

        if form.is_valid():
            if discussion.moderate_all:
                status = Comment.STATUS_POSTED
            else:
                status = Comment.STATUS_APPROVED
            new_comment, created = Comment.objects.get_or_create(
                event=event,
                comment=form.cleaned_data['comment'],
                reply_to=form.cleaned_data['reply_to'],
                user=request.user,
                status=status,
            )
            if form.cleaned_data['name']:
                first_name, last_name = _first_last_name(
                    form.cleaned_data['name']
                )
                request.user.first_name = first_name
                request.user.last_name = last_name
                request.user.save()
            if created:
                if discussion.moderate_all and _can_manage_comments:
                    new_comment.status = Comment.STATUS_APPROVED
                    new_comment.save()
                if discussion.moderate_all and discussion.notify_all:
                    sending.send_moderator_notifications(new_comment, request)

        else:
            return http.HttpResponseBadRequest(str(form.errors))

    comments = Comment.objects.filter(
        event=event,
        reply_to__isnull=True
    )

    if request.user.is_authenticated():
        query_filter = Q(status=Comment.STATUS_APPROVED) | Q(user=request.user)
        if _can_manage_comments:
            query_filter = query_filter | Q(status=Comment.STATUS_POSTED)
    else:
        query_filter = Q(status=Comment.STATUS_APPROVED)

    comments = comments.filter(query_filter)

    sub_context = {
        'comments': comments.order_by('created'),
        'discussion': discussion,
        'request': request,
        'Comment': Comment,
        'can_manage_comments': _can_manage_comments,
        'root': True,
        'query_filter': query_filter,
    }
    context['html'] = render_to_string(
        'comments/comments.html',
        sub_context
    )
    context['can_manage_comments'] = _can_manage_comments
    context['latest_comment'] = get_latest_comment(
        event,
        include_posted=_can_manage_comments
    )
    return context


@cache_page(5)  # must match interval in comments.js
@json_view
def event_data_latest(request, id):
    cache_key = 'latest_comment:%s' % (id,)
    include_posted = bool(request.GET.get(
        'include_posted'
    ))
    cache_key += ':%s' % include_posted

    latest_comment = cache.get(cache_key, -1)
    if latest_comment == -1:
        try:
            discussion = Discussion.objects.get(event__pk=id, enabled=True)
        except Discussion.DoesNotExist:
            return http.HttpResponseBadRequest('Discussion not enabled')
        latest_comment = get_latest_comment(
            discussion.event_id,
            include_posted=include_posted,
        )
        cache.set(cache_key, latest_comment, 24 * 60 * 60)
    return {'latest_comment': latest_comment}


def _first_last_name(name):
    _split = name.rsplit(None, 1)
    if len(_split) == 1:
        return name, ''
    else:
        return _split[0], _split[1]


@json_view
def user_name(request):
    if (
        request.user.is_authenticated() and
        not request.user.get_full_name() and
        request.user.email
    ):
        # try to look it up on Mozillians
        # but first, if this fails the name won't get update and we'll keep
        # trying over and over
        cache_key = 'mozillians-fullname-query-%s' % request.user.pk
        if not cache.get(cache_key):
            full_name = fetch_user_name(request.user.email)
            if full_name:
                first_name, last_name = _first_last_name(full_name)
                request.user.first_name = first_name
                request.user.last_name = last_name
                request.user.save()
            cache.set(cache_key, 1, 60 * 60 * 24)

    name = ''
    if request.user.is_authenticated():
        name = request.user.get_full_name()
    return {'name': name}


@transaction.atomic
def unsubscribe(request, identifier, id=None):
    context = {}
    event = discussion = None
    if id:
        discussion = get_object_or_404(Discussion, id=id)
        event = discussion.event

    context['event'] = event
    cache_key = 'unsubscribe-%s' % identifier
    user_id = cache.get(cache_key)
    if user_id:
        user = get_object_or_404(User, id=user_id)
    else:
        user = None
    context['user'] = user

    if request.method == 'POST':
        if not user:
            return http.HttpResponseBadRequest('No user')
        Unsubscription.objects.get_or_create(
            user=user,
            discussion=discussion
        )
        cache.delete(cache_key)
        if discussion:
            return redirect('comments:unsubscribed', discussion.id)
        else:
            return redirect('comments:unsubscribed_all')

    return render(request, 'comments/unsubscribe.html', context)


def unsubscribed(request, id=None):
    context = {}
    event = None
    if id:
        discussion = get_object_or_404(Discussion, id=id)
        event = discussion.event
    context['event'] = event
    return render(request, 'comments/unsubscribed.html', context)


def approve_immediately(request, identifier, id):
    comment = get_object_or_404(Comment, id=id)
    context = {
        'comment': comment,
        'comment_found': False
    }
    cache_key = 'approve-%s' % identifier
    comment_id = cache.get(cache_key)
    if comment_id and int(comment_id) == comment.id:
        comment = get_object_or_404(Comment, id=comment_id)
        comment.status = Comment.STATUS_APPROVED
        comment.save()
        context['comment_found'] = True
    return render(request, 'comments/approved.html', context)


def remove_immediately(request, identifier, id):
    comment = get_object_or_404(Comment, id=id)
    context = {
        'comment': comment,
        'comment_found': False
    }
    cache_key = 'remove-%s' % identifier
    comment_id = cache.get(cache_key)
    if comment_id and int(comment_id) == comment.id:
        comment.status = Comment.STATUS_REMOVED
        comment.save()
        context['comment_found'] = True
    return render(request, 'comments/removed.html', context)
