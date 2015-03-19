from django.contrib import messages
from django.shortcuts import render, redirect
from django.db import transaction

from airmozilla.base.utils import paginate
from airmozilla.main.models import Channel
from airmozilla.manage import forms
from airmozilla.staticpages.models import StaticPage

from .decorators import (
    staff_required,
    permission_required,
    cancel_redirect
)


@staff_required
@permission_required('staticpages.change_staticpage')
def staticpages(request):
    staticpages_paged = paginate(
        StaticPage.objects.all(),
        request.GET.get('page'),
        10
    )
    context = {
        'paginate': staticpages_paged,
    }
    return render(request, 'manage/staticpages.html', context)


@staff_required
@permission_required('staticpages.change_staticpage')
@cancel_redirect('manage:staticpages')
@transaction.commit_on_success
def staticpage_new(request):
    if request.method == 'POST':
        form = forms.StaticPageEditForm(request.POST, instance=StaticPage())
        if form.is_valid():
            instance = form.save()
            instance.save()
            if instance.url.startswith('sidebar_'):
                __, location, channel_slug = instance.url.split('_', 2)
                channel = Channel.objects.get(
                    slug=channel_slug
                )
                instance.title = 'Sidebar (%s) %s' % (location, channel.name)
                instance.save()
            messages.success(request, 'Page created.')
            return redirect('manage:staticpages')
    else:
        form = forms.StaticPageEditForm()
        form.fields['url'].help_text = (
            "for example '/my-page' or 'sidebar_top_main' (see below)"
        )
    return render(
        request,
        'manage/staticpage_new.html',
        {'form': form,
         'channels': Channel.objects.all().order_by('slug')}
    )


@staff_required
@permission_required('staticpages.change_staticpage')
@cancel_redirect('manage:staticpages')
@transaction.commit_on_success
def staticpage_edit(request, id):
    staticpage = StaticPage.objects.get(id=id)
    if request.method == 'POST':
        form = forms.StaticPageEditForm(request.POST, instance=staticpage)
        if form.is_valid():
            instance = form.save()
            if instance.url.startswith('sidebar_'):
                __, location, channel_slug = instance.url.split('_', 2)
                channel = Channel.objects.get(
                    slug=channel_slug
                )
                instance.title = 'Sidebar (%s) %s' % (location, channel.name)
                instance.save()
            messages.info(request, 'Page %s saved.' % staticpage.url)
            return redirect('manage:staticpages')
    else:
        form = forms.StaticPageEditForm(instance=staticpage)
    return render(request, 'manage/staticpage_edit.html',
                  {'form': form, 'staticpage': staticpage})


@staff_required
@permission_required('staticpages.delete_staticpage')
@transaction.commit_on_success
def staticpage_remove(request, id):
    if request.method == 'POST':
        staticpage = StaticPage.objects.get(id=id)
        staticpage.delete()
        messages.info(request, 'Page "%s" removed.' % staticpage.title)
    return redirect('manage:staticpages')
