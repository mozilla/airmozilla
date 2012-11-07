import logging
from django.conf import settings
from django.contrib import auth
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from django.contrib import messages

from django_browserid.base import get_audience
from django_browserid.auth import verify
from django_browserid.forms import BrowserIDForm
from .mozillians import is_vouched, BadStatusCodeError


@require_POST
def mozilla_browserid_verify(request):
    """Custom BrowserID verifier for mozilla addresses."""
    form = BrowserIDForm(request.POST)
    if form.is_valid():
        assertion = form.cleaned_data['assertion']
        audience = get_audience(request)
        result = verify(assertion, audience)
        try:
            if result and (
                result['email'].split('@')[-1]
                in settings.ALLOWED_BID
                or is_vouched(result['email'])
            ):
                user = auth.authenticate(
                    assertion=assertion,
                    audience=audience
                )
                auth.login(request, user)
                return redirect(settings.LOGIN_REDIRECT_URL)
            elif result:
                messages.error(
                    request,
                    'Email (%s) authenticated but not vouched for' %
                    result['email']
                )
        except BadStatusCodeError:
            logging.error('Unable to call out to mozillians',
                          exc_info=True)
            messages.error(
                request,
                'Email (%s) authenticated but unable to connect to '
                'Mozillians to see if are vouched. ' %
                result['email']
            )

    return redirect(settings.LOGIN_REDIRECT_URL_FAILURE)


def login_failure(request):
    return render(request, 'auth/login_failure.html')
