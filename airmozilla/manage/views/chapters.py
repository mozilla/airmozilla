from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from django.core.urlresolvers import reverse

from airmozilla.main.models import Event, Chapter
from airmozilla.manage import forms

from .decorators import (
    staff_required,
    permission_required,
    cancel_redirect
)


@staff_required
@permission_required('main.change_chapter')
def event_chapters(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    context = {}
    context['event'] = event
    context['chapters'] = Chapter.objects.filter(event=event)
    return render(request, 'manage/event_chapters.html', context)


@staff_required
@permission_required('main.add_chapter')
@cancel_redirect(
    lambda r, event_id: reverse('manage:event_chapters', args=(event_id,))
)
@transaction.atomic
def event_chapter_new(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        form = forms.EventChapterEditForm(
            request.POST,
            instance=Chapter(user=request.user, event=event)
        )
        if form.is_valid():
            form.save()
            messages.success(request, 'Chapter created.')
            return redirect('manage:event_chapters', event.id)
    else:
        form = forms.EventChapterEditForm()
    context = {'form': form}
    return render(request, 'manage/event_chapter_new.html', context)


@staff_required
@permission_required('main.change_chapter')
@cancel_redirect(
    lambda r, event_id, id: reverse('manage:event_chapters', args=(event_id,))
)
@transaction.atomic
def event_chapter_edit(request, event_id, id):
    chapter = Chapter.objects.get(id=id, event__id=event_id)
    if request.method == 'POST':
        form = forms.EventChapterEditForm(request.POST, instance=chapter)
        if form.is_valid():
            form.save()
            messages.info(request, 'Chapter saved.')
            return redirect('manage:event_chapters', chapter.event.id)
    else:
        form = forms.EventChapterEditForm(instance=chapter)
    context = {
        'form': form,
        'chapter': chapter,
    }
    return render(request, 'manage/event_chapter_edit.html', context)


@staff_required
@permission_required('main.delete_chapter')
@transaction.atomic
def event_chapter_delete(request, event_id, id):
    if request.method == 'POST':
        chapter = Chapter.objects.get(id=id, event__id=event_id)
        chapter.delete()
        messages.info(request, 'Chapter deleted.')
    return redirect('manage:event_chapters', chapter.event.id)
