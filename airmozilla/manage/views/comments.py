from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.db.models import Q

from airmozilla.base.utils import paginate
from airmozilla.manage import forms
from airmozilla.comments.models import Comment

from .decorators import staff_required, permission_required


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
