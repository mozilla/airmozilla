from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.db import transaction
from django.contrib.flatpages.models import FlatPage


from airmozilla.base.utils import paginate
from airmozilla.main.models import Channel
from airmozilla.manage import forms

from .decorators import (
    staff_required,
    permission_required,
    cancel_redirect
)


@staff_required
@permission_required('flatpages.change_flatpage')
def flatpages(request):
    flatpages_paged = paginate(FlatPage.objects.all(),
                               request.GET.get('page'), 10)
    return render(request, 'manage/flatpages.html',
                  {'paginate': flatpages_paged})


@staff_required
@permission_required('flatpages.change_flatpage')
@cancel_redirect('manage:flatpages')
@transaction.commit_on_success
def flatpage_new(request):
    if request.method == 'POST':
        form = forms.FlatPageEditForm(request.POST, instance=FlatPage())
        if form.is_valid():
            instance = form.save()
            instance.sites.add(settings.SITE_ID)
            instance.save()
            if instance.url.startswith('sidebar_'):
                __, location, channel_slug = instance.url.split('_', 2)
                channel = Channel.objects.get(
                    slug=channel_slug
                )
                instance.title = 'Sidebar (%s) %s' % (location, channel.name)
                instance.save()
            messages.success(request, 'Page created.')
            return redirect('manage:flatpages')
    else:
        form = forms.FlatPageEditForm()
        form.fields['url'].help_text = (
            "for example '/my-page' or 'sidebar_top_main' (see below)"
        )
    return render(
        request,
        'manage/flatpage_new.html',
        {'form': form,
         'channels': Channel.objects.all().order_by('slug')}
    )


@staff_required
@permission_required('flatpages.change_flatpage')
@cancel_redirect('manage:flatpages')
@transaction.commit_on_success
def flatpage_edit(request, id):
    """Editing an flatpage."""
    page = FlatPage.objects.get(id=id)
    if request.method == 'POST':
        form = forms.FlatPageEditForm(request.POST, instance=page)
        if form.is_valid():
            instance = form.save()
            if instance.url.startswith('sidebar_'):
                __, location, channel_slug = instance.url.split('_', 2)
                channel = Channel.objects.get(
                    slug=channel_slug
                )
                instance.title = 'Sidebar (%s) %s' % (location, channel.name)
                instance.save()
            messages.info(request, 'Page %s saved.' % page.url)
            return redirect('manage:flatpages')
    else:
        form = forms.FlatPageEditForm(instance=page)
    return render(request, 'manage/flatpage_edit.html',
                  {'form': form, 'flatpage': page})


@staff_required
@permission_required('flatpages.delete_flatpage')
@transaction.commit_on_success
def flatpage_remove(request, id):
    if request.method == 'POST':
        flatpage = FlatPage.objects.get(id=id)
        flatpage.delete()
        messages.info(request, 'Page "%s" removed.' % flatpage.title)
    return redirect('manage:flatpages')
