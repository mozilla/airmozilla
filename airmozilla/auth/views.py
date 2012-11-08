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
from airmozilla.main.models import UserProfile


@require_POST
def mozilla_browserid_verify(request):
    """Custom BrowserID verifier for mozilla addresses."""
    form = BrowserIDForm(request.POST)
    if form.is_valid():
        assertion = form.cleaned_data['assertion']
        audience = get_audience(request)
        result = verify(assertion, audience)
        try:
            _ok_assertion = False
            _is_contributor = False
            if result:
                _domain = result['email'].split('@')[-1]
                if _domain in settings.ALLOWED_BID:
                    _ok_assertion = True
                elif is_vouched(result['email']):
                    _ok_assertion = True
                    _is_contributor = True

            if _ok_assertion:
                user = auth.authenticate(
                    assertion=assertion,
                    audience=audience
                )
                auth.login(request, user)
                if _is_contributor:
                    try:
                        profile = user.get_profile()
                        if not profile.contributor:
                            profile.contributor = True
                            profile.save()
                    except UserProfile.DoesNotExist:
                        profile = UserProfile.objects.create(
                            user=user,
                            contributor=True
                        )
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
