from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.db import transaction

from airmozilla.main.models import Topic
from airmozilla.manage import forms

from .decorators import (
    staff_required,
    permission_required,
    cancel_redirect
)


@staff_required
@permission_required('main.change_topic')
def topics(request):
    context = {}
    topics = Topic.objects.all()
    context['topics'] = topics

    return render(request, 'manage/topics.html', context)


@permission_required('main.change_topic')
@cancel_redirect('manage:topics')
@transaction.atomic
def topic_edit(request, id):
    topic = get_object_or_404(Topic, id=id)

    if request.method == 'POST':
        form = forms.TopicEditForm(request.POST, instance=topic)
        if form.is_valid():
            form.save()
            messages.info(request, 'Topic "%s" saved.' % topic)
            return redirect('manage:topics')
    else:
        form = forms.TopicEditForm(instance=topic)

    context = {
        'form': form,
        'topic': topic,
    }

    return render(request, 'manage/topic_edit.html', context)


@staff_required
@permission_required('main.add_topic')
@cancel_redirect('manage:events')
@transaction.atomic
def topic_new(request):
    if request.method == 'POST':
        form = forms.TopicEditForm(request.POST, instance=Topic())
        if form.is_valid():
            form.save()
            messages.success(request, 'Topic created.')
            return redirect('manage:topics')
    else:
        initial = {
            'sort_order': Topic.objects.all().count() + 1
        }
        form = forms.TopicEditForm(initial=initial)
    return render(request, 'manage/topic_new.html', {'form': form})


@require_POST
@staff_required
@permission_required('main.delete_topic')
@transaction.atomic
def topic_remove(request, id):
    topic = get_object_or_404(Topic, id=id)
    topic.delete()
    messages.info(request, 'Topic "%s" removed.' % topic.topic)

    return redirect('manage:topics')
