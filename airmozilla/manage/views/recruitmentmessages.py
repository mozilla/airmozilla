from django.contrib import messages
from django.shortcuts import render, redirect
from django.db import transaction

from airmozilla.main.models import Event, RecruitmentMessage
from airmozilla.manage import forms

from .decorators import (
    staff_required,
    permission_required,
    cancel_redirect
)


@staff_required
@permission_required('main.change_recruitmentmessage')
def recruitmentmessages(request):
    context = {}
    context['recruitmentmessages'] = RecruitmentMessage.objects.all()

    def count_events(this):
        return Event.objects.filter(recruitmentmessage=this).count()

    context['count_events'] = count_events
    return render(request, 'manage/recruitmentmessages.html', context)


@staff_required
@permission_required('main.add_recruitmentmessage')
@cancel_redirect('manage:recruitmentmessages')
@transaction.commit_on_success
def recruitmentmessage_new(request):
    if request.method == 'POST':
        form = forms.RecruitmentMessageEditForm(
            request.POST,
            instance=RecruitmentMessage()
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Recruitment message created.')
            return redirect('manage:recruitmentmessages')
    else:
        form = forms.RecruitmentMessageEditForm()
    context = {'form': form}
    return render(request, 'manage/recruitmentmessage_new.html', context)


@staff_required
@permission_required('main.change_recruitmentmessage')
@cancel_redirect('manage:recruitmentmessages')
@transaction.commit_on_success
def recruitmentmessage_edit(request, id):
    msg = RecruitmentMessage.objects.get(id=id)
    if request.method == 'POST':
        form = forms.RecruitmentMessageEditForm(request.POST, instance=msg)
        if form.is_valid():
            msg = form.save()
            messages.info(request, 'Recruitment message saved.')
            return redirect('manage:recruitmentmessages')
    else:
        form = forms.RecruitmentMessageEditForm(instance=msg)
    context = {
        'form': form,
        'recruitmentmessage': msg,
        'events_using': (
            Event.objects.filter(recruitmentmessage=msg).order_by('title')
        )
    }
    return render(request, 'manage/recruitmentmessage_edit.html', context)


@staff_required
@permission_required('main.delete_recruitmentmessage')
@transaction.commit_on_success
def recruitmentmessage_delete(request, id):
    if request.method == 'POST':
        msg = RecruitmentMessage.objects.get(id=id)
        msg.delete()
        messages.info(request, 'Recruitment message deleted.')
    return redirect('manage:recruitmentmessages')
