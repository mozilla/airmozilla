from django.contrib import messages
from django.shortcuts import render, redirect
from django.db import transaction

from airmozilla.main.models import Channel
from airmozilla.manage import forms

from .decorators import (
    staff_required,
    permission_required,
    cancel_redirect
)


@staff_required
@permission_required('main.change_channel')
def channels(request):
    channels = Channel.objects.all()
    return render(request, 'manage/channels.html',
                  {'channels': channels})


@staff_required
@permission_required('main.add_channel')
@cancel_redirect('manage:channels')
@transaction.commit_on_success
def channel_new(request):
    use_ace = bool(int(request.GET.get('use_ace', 1)))
    if request.method == 'POST':
        form = forms.ChannelForm(request.POST, instance=Channel())
        if form.is_valid():
            form.save()
            messages.success(request, 'Channel created.')
            return redirect('manage:channels')
    else:
        form = forms.ChannelForm()
    return render(request,
                  'manage/channel_new.html',
                  {'form': form,
                   'use_ace': use_ace})


@staff_required
@permission_required('main.change_channel')
@cancel_redirect('manage:channels')
@transaction.commit_on_success
def channel_edit(request, id):
    channel = Channel.objects.get(id=id)
    use_ace = bool(int(request.GET.get('use_ace', 1)))
    if request.method == 'POST':
        form = forms.ChannelForm(request.POST, request.FILES, instance=channel)
        if form.is_valid():
            channel = form.save()
            messages.info(request, 'Channel "%s" saved.' % channel.name)
            return redirect('manage:channels')
    else:
        form = forms.ChannelForm(instance=channel)
    return render(request, 'manage/channel_edit.html',
                  {'form': form, 'channel': channel,
                   'use_ace': use_ace})


@staff_required
@permission_required('main.delete_channel')
@transaction.commit_on_success
def channel_remove(request, id):
    if request.method == 'POST':
        channel = Channel.objects.get(id=id)
        channel.delete()
        messages.info(request, 'Channel "%s" removed.' % channel.name)
    return redirect('manage:channels')
