from raven import Client

from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings

from airmozilla.manage import forms
from .decorators import superuser_required


@superuser_required
def error_trigger(request):
    context = {}
    if request.method == 'POST':
        form = forms.TriggerErrorForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['capture_with_raven']:
                try:
                    dsn = settings.RAVEN_CONFIG['dsn']
                except AttributeError:
                    messages.error(
                        request,
                        "No settings.RAVEN_CONFIG['dsn'] set up"
                    )
                    return redirect('manage:error_trigger')

                client = Client(dsn)
                try:
                    raise NameError(form.cleaned_data['message'])
                except NameError:
                    messages.info(
                        request,
                        str(client.captureException())
                    )
                return redirect('manage:error_trigger')

            raise NameError(
                'MANUAL ERROR TRIGGER: %s' % form.cleaned_data['message']
            )
    else:
        form = forms.TriggerErrorForm()

    context['form'] = form

    return render(request, 'manage/error_trigger.html', context)
