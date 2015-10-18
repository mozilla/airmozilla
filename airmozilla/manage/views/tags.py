import collections

from django import http
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.db.models import Count
from django.core.urlresolvers import reverse

from jsonview.decorators import json_view

from airmozilla.main.models import Event, Tag
from airmozilla.manage import forms

from .decorators import (
    staff_required,
    permission_required,
    cancel_redirect
)


@staff_required
@permission_required('main.change_event')
def tags(request):
    return render(request, 'manage/tags.html')


@staff_required
@permission_required('main.change_event')
@json_view
def tags_data(request):
    context = {}
    tags = []

    counts = {}
    qs = (
        Event.tags.through.objects.all()
        .values('tag_id').annotate(Count('tag'))
    )
    for each in qs:
        counts[each['tag_id']] = each['tag__count']

    _repeats = collections.defaultdict(int)
    for tag in Tag.objects.all():
        _repeats[tag.name.lower()] += 1

    for tag in Tag.objects.all():
        tags.append({
            'name': tag.name,
            'id': tag.id,
            '_usage_count': counts.get(tag.id, 0),
            '_repeated': _repeats[tag.name.lower()] > 1,
        })
    context['tags'] = tags
    context['urls'] = {
        'manage:tag_edit': reverse('manage:tag_edit', args=(0,)),
        'manage:tag_remove': reverse('manage:tag_remove', args=(0,)),
    }
    return context


@staff_required
@permission_required('main.change_event')
@cancel_redirect('manage:tags')
@transaction.atomic
def tag_edit(request, id):
    tag = get_object_or_404(Tag, id=id)
    if request.method == 'POST':
        form = forms.TagEditForm(request.POST, instance=tag)
        if form.is_valid():
            tag = form.save()
            if Tag.objects.filter(name__iexact=tag.name).exclude(pk=tag.pk):
                messages.warning(
                    request,
                    "The tag you edited already exists with that same case "
                    "insensitive spelling."
                )
                return redirect('manage:tag_edit', tag.pk)
            else:
                edit_url = reverse('manage:tag_edit', args=(tag.pk,))
                messages.info(
                    request,
                    'Tag "%s" saved. [Edit again](%s)' % (tag, edit_url)
                )
                return redirect('manage:tags')
    else:
        form = forms.TagEditForm(instance=tag)
    repeated = Tag.objects.filter(name__iexact=tag.name).count()
    context = {
        'form': form,
        'tag': tag,
        'repeated': repeated,
        'is_repeated': repeated > 1
    }

    if repeated > 1:
        context['repeated_form'] = forms.TagMergeRepeatedForm(this_tag=tag)
    else:
        context['merge_form'] = forms.TagMergeForm(this_tag=tag)
    return render(request, 'manage/tag_edit.html', context)


@staff_required
@permission_required('main.delete_tag')
@transaction.atomic
def tag_remove(request, id):
    if request.method == 'POST':
        tag = get_object_or_404(Tag, id=id)
        for event in Event.objects.filter(tags=tag):
            event.tags.remove(tag)
        messages.info(request, 'Tag "%s" removed.' % tag.name)
        tag.delete()
    return redirect(reverse('manage:tags'))


@staff_required
@permission_required('main.change_tag')
@cancel_redirect('manage:tags')
@transaction.atomic
def tag_merge(request, id):
    tag = get_object_or_404(Tag, id=id)
    form = forms.TagMergeForm(tag, request.POST)
    if not form.is_valid():
        return http.HttpResponseBadRequest(form.errors)
    destination = get_object_or_404(
        Tag,
        name__iexact=form.cleaned_data['name']
    )

    count_events = 0
    for event in Event.objects.filter(tags=tag):
        event.tags.remove(tag)
        event.tags.add(destination)
        count_events += 1
    tag.delete()

    messages.info(
        request,
        '"%s" is the new cool tag (affected %s events)' % (
            destination.name,
            count_events,
        )
    )

    return redirect('manage:tags')


@staff_required
@permission_required('main.change_tag')
@cancel_redirect('manage:tags')
@transaction.atomic
def tag_merge_repeated(request, id):
    tag = get_object_or_404(Tag, id=id)
    tag_to_keep = get_object_or_404(Tag, id=request.POST['keep'])

    merge_count = 0
    other_tags = (
        Tag.objects
        .filter(name__iexact=tag.name)
        .exclude(id=tag_to_keep.id)
    )
    for t in other_tags:
        for event in Event.objects.filter(tags=t):
            event.tags.remove(t)
            event.tags.add(tag_to_keep)
        t.delete()
        merge_count += 1

    messages.info(
        request,
        'Merged ' +
        ('1 tag' if merge_count == 1 else '%d tag' % merge_count) +
        ' into "%s".' % tag_to_keep.name
    )

    return redirect('manage:tags')
