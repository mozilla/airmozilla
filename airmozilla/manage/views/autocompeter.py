from StringIO import StringIO

from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.contrib.sites.requests import RequestSite

from jsonview.decorators import json_view

from .decorators import superuser_required
from airmozilla.manage.autocompeter import update, stats, test
from airmozilla.manage import forms


@superuser_required
def autocompeter_home(request):
    if request.method == 'POST':
        form = forms.AutocompeterUpdateForm(request.POST)
        if form.is_valid():
            options = form.cleaned_data
            out = StringIO()
            options['out'] = out
            update(**options)
            messages.success(
                request,
                out.getvalue()
            )
            return redirect('manage:autocompeter')

    else:
        initial = {
            'verbose': True,
            'max_': 100,
            'since': 10,
        }
        form = forms.AutocompeterUpdateForm(initial=initial)

    context = {
        'form': form,
    }
    return render(request, 'manage/autocompeter.html', context)


@superuser_required
@json_view
def autocompeter_stats(request):
    return stats()


@superuser_required
@json_view
def autocompeter_test(request):
    domain = getattr(
        settings,
        'AUTOCOMPETER_DOMAIN',
        RequestSite(request).domain
    )
    return test(request.GET['term'], domain=domain)
