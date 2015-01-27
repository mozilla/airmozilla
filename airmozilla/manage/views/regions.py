from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.db import transaction

from airmozilla.main.models import (
    Region,
)
from airmozilla.manage import forms

from .decorators import (
    staff_required,
    permission_required,
    cancel_redirect
)


@staff_required
@permission_required('main.change_region')
def regions(request):
    context = {}
    regions = Region.objects.all()
    context['regions'] = regions

    return render(request, 'manage/regions.html', context)


@permission_required('main.change_region')
@cancel_redirect('manage:regions')
@transaction.commit_on_success
def region_edit(request, id):
    region = get_object_or_404(Region, id=id)

    if request.method == 'POST':
        form = forms.RegionEditForm(request.POST, instance=region)
        if form.is_valid():
            form.save()
            messages.info(request, 'Region "%s" saved.' % region)
            return redirect('manage:regions')
    else:
        form = forms.RegionEditForm(instance=region)

    context = {
        'form': form,
        'region': region,
    }

    return render(request, 'manage/region_edit.html', context)


@staff_required
@permission_required('main.add_region')
@cancel_redirect('manage:events')
@transaction.commit_on_success
def region_new(request):
    if request.method == 'POST':
        form = forms.RegionEditForm(request.POST, instance=Region())
        if form.is_valid():
            form.save()
            messages.success(request, 'Region created.')
            return redirect('manage:regions')
    else:
        form = forms.RegionEditForm()
    return render(request, 'manage/region_new.html', {'form': form})


@require_POST
@staff_required
@permission_required('main.delete_region')
@transaction.commit_on_success
def region_remove(request, id):
    region = get_object_or_404(Region, id=id)
    region.delete()
    messages.info(request, 'Region "%s" removed.' % region.name)

    return redirect('manage:regions')
