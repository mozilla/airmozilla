from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Max

from jsonview.decorators import json_view

from airmozilla.main.models import URLMatch, URLTransform
from airmozilla.manage import forms
from airmozilla.manage import url_transformer

from .decorators import staff_required, permission_required


@staff_required
@permission_required('main.change_urlmatch')
def url_transforms(request):
    data = {}

    matchers = []
    for matcher in URLMatch.objects.order_by('-modified'):
        matchers.append((
            matcher,
            URLTransform.objects.filter(match=matcher).order_by('order')
        ))
    data['matchers'] = matchers

    available_variables = []
    url_transform_passwords = settings.URL_TRANSFORM_PASSWORDS
    for key in sorted(url_transform_passwords):
        available_variables.append("{{ password('%s') }}" % key)
    data['available_variables'] = available_variables

    return render(request, 'manage/url_transforms.html', data)


@staff_required
@permission_required('main.change_urlmatch')
@transaction.commit_on_success
def url_match_new(request):
    if request.method == 'POST':
        form = forms.URLMatchForm(data=request.POST)
        if form.is_valid():
            form.save()
            messages.info(request, 'New match added.')
            return redirect('manage:url_transforms')
    else:
        form = forms.URLMatchForm()
    return render(request, 'manage/url_match_new.html', {'form': form})


@staff_required
@permission_required('main.change_urlmatch')
@transaction.commit_on_success
@require_POST
def url_match_remove(request, id):
    url_match = get_object_or_404(URLMatch, id=id)
    name = url_match.name
    for transform in URLTransform.objects.filter(match=url_match):
        transform.delete()
    url_match.delete()

    messages.info(request, "URL Match '%s' removed." % name)
    return redirect('manage:url_transforms')


@staff_required
@json_view
def url_match_run(request):
    url = request.GET['url']
    result, error = url_transformer.run(url, dry=True)
    return {'result': result, 'error': error}


@staff_required
@permission_required('main.change_urlmatch')
@transaction.commit_on_success
@require_POST
@json_view
def url_transform_add(request, id):
    match = get_object_or_404(URLMatch, id=id)
    find = request.POST['find']
    replace_with = request.POST['replace_with']
    next_order = (
        URLTransform.objects
        .filter(match=match)
        .aggregate(Max('order'))
    )
    if next_order['order__max'] is None:
        next_order = 1
    else:
        next_order = next_order['order__max'] + 1
    transform = URLTransform.objects.create(
        match=match,
        find=find,
        replace_with=replace_with,
        order=next_order,
    )
    transform_as_dict = {
        'id': transform.id,
        'find': transform.find,
        'replace_with': transform.replace_with,
        'order': transform.order,
    }
    return {'transform': transform_as_dict}


@staff_required
@permission_required('main.change_urlmatch')
@transaction.commit_on_success
@require_POST
@json_view
def url_transform_remove(request, id, transform_id):
    match = get_object_or_404(URLMatch, id=id)
    transform = get_object_or_404(URLTransform, id=transform_id, match=match)
    transform.delete()
    return True


@staff_required
@permission_required('main.change_urlmatch')
@transaction.commit_on_success
@require_POST
@json_view
def url_transform_edit(request, id, transform_id):
    match = get_object_or_404(URLMatch, id=id)
    transform = get_object_or_404(URLTransform, id=transform_id, match=match)
    transform.find = request.POST['find']
    transform.replace_with = request.POST['replace_with']
    transform.save()
    return True
