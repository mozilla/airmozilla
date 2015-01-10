from django import http
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.db import transaction

from airmozilla.main.models import (
    Approval,
    Event,
    SuggestedEvent
)
from airmozilla.manage import forms

from .decorators import staff_required, permission_required


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
