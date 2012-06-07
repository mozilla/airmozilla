from django.conf import settings
from django.contrib import auth
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from django_browserid.auth import get_audience, verify
from django_browserid.forms import BrowserIDForm


@require_POST
def mozilla_browserid_verify(request):
    """Custom BrowserID verifier for mozilla addresses."""
    form = BrowserIDForm(request.POST)
    if form.is_valid():
        assertion = form.cleaned_data['assertion']
        audience = get_audience(request)
        result = verify(assertion, audience)
        if result and result['email'].split('@')[-1] in settings.ALLOWED_BID:
            user = auth.authenticate(assertion=assertion, audience=audience)
            auth.login(request, user)
            return redirect(settings.LOGIN_REDIRECT_URL)
    return redirect(settings.LOGIN_REDIRECT_URL_FAILURE)

def login_failure(request):
    return render(request, 'login_failure.html')
