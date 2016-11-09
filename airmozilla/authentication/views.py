import logging
import urllib
import hashlib
import base64

import requests

from django import http
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.views.decorators.http import require_POST
from django.contrib.auth import get_user_model, login
from django.utils.encoding import smart_bytes

from csp.decorators import csp_update

from airmozilla.base.mozillians import is_vouched, BadStatusCodeError
from airmozilla.main.models import UserProfile, get_profile_safely

from django_browserid.views import Verify
from django_browserid.http import JSONResponse

logger = logging.getLogger('auth')


User = get_user_model()


class CustomBrowserIDVerify(Verify):

    def login_failure(self, error=None):
        """
        Different to make it not yield a 403 error.
        """
        if error:
            logger.error(error)

        return JSONResponse({'redirect': self.failure_url})

    def login_success(self):
        """the user passed the BrowserID hurdle, but do they have a valid
        email address or vouched for in Mozillians"""
        domain = self.user.email.split('@')[-1].lower()
        try:
            if domain in settings.ALLOWED_BID:
                # If you were a contributor before, undo that.
                # This might be the case when we extend settings.ALLOWED_BID
                # with new domains and people with those domains logged
                # in before.
                try:
                    # This works because of the OneToOneField and
                    # related_name='profile' on the UserProfile class.
                    profile = self.user.profile
                    # if you were a contributor before, undo that now
                    if profile.contributor:
                        profile.contributor = False
                        profile.save()
                except UserProfile.DoesNotExist:
                    pass

            elif is_vouched(self.user.email):
                try:
                    profile = self.user.profile
                    if not profile.contributor:
                        profile.contributor = True
                        profile.save()
                except UserProfile.DoesNotExist:
                    profile = UserProfile.objects.create(
                        user=self.user,
                        contributor=True
                    )
            else:
                messages.error(
                    self.request,
                    'Email {0} authenticated but not vouched for'
                    .format(self.user.email)
                )
                return self.login_failure()
        except BadStatusCodeError:
            logger.error('Unable to call out to mozillians', exc_info=True)
            messages.error(
                self.request,
                'Email {0} authenticated but unable to connect to '
                'Mozillians to see if are vouched. '
                .format(self.user.email)
            )
            return self.login_failure()

        return super(CustomBrowserIDVerify, self).login_success()


@csp_update(
    CONNECT_SRC=settings.AUTH0_DOMAIN,
    SCRIPT_SRC=['cdn.auth0.com', 'secure.gravatar.com'],
    IMG_SRC='cdn.auth0.com',
)
def signin(request):
    context = {
        'AUTH0_CLIENT_ID': settings.AUTH0_CLIENT_ID,
        'AUTH0_DOMAIN': settings.AUTH0_DOMAIN,
        'AUTH0_CALLBACK_URL': settings.AUTH0_CALLBACK_URL,
    }
    return render(request, 'authentication/signin.html', context)


@require_POST
def signout(request):
    logout(request)
    url = 'https://' + settings.AUTH0_DOMAIN + '/v2/logout'
    url += '?' + urllib.urlencode({
        'returnTo': settings.AUTH_SIGNOUT_URL,
        'client_id': settings.AUTH0_CLIENT_ID,
    })
    return redirect(url)


def callback(request):
    """Much of this is copied from the callback done in django_auth0
    but with the major difference that we handle checking if non-staff
    are vouched Mozillians."""
    code = request.GET.get('code', '')
    if not code:
        # If the user is blocked, we will never be called back with a code.
        # What Auth0 does is that it calls the callback but with extra
        # query string parameters.
        if request.GET.get('error'):
            messages.error(
                request,
                "Unable to sign in because of an error from Auth0. "
                "({})".format(
                    request.GET.get(
                        'error_description',
                        request.GET['error']
                    )
                )
            )
            return redirect('authentication:signin')
        return http.HttpResponseBadRequest("Missing 'code'")
    token_url = 'https://{}/oauth/token'.format(settings.AUTH0_DOMAIN)
    token_payload = {
        'client_id': settings.AUTH0_CLIENT_ID,
        'client_secret': settings.AUTH0_SECRET,
        'redirect_uri': settings.AUTH0_CALLBACK_URL,
        'code': code,
        'grant_type': 'authorization_code',
    }
    token_info = requests.post(
        token_url,
        json=token_payload,
    ).json()

    if not token_info.get('access_token'):
        messages.error(
            request,
            'Unable to authenticate with Auth0. Most commonly this '
            'happens because the authentication token has expired. '
            'Please refresh and try again.'
        )
        return redirect('authentication:signin')

    user_url = 'https://{}/userinfo'.format(
        settings.AUTH0_DOMAIN,
    )
    user_url += '?' + urllib.urlencode({
        'access_token': token_info['access_token'],
    })
    user_response = requests.get(user_url)
    if user_response.status_code != 200:
        messages.error(
            request,
            'Unable to retrieve user info from Auth0 ({}, {!r})'.format(
                user_response.status_code,
                user_response.text
            )
        )
        return redirect('authentication:signin')
    user_info = user_response.json()
    assert user_info['email'], user_info
    try:
        user = get_user(user_info)
    except BadStatusCodeError:
        messages.error(
            request,
            'Email {} authenticated but unable to connect to '
            'Mozillians.org to see if are vouched. Please try again '
            'in a minute.'.format(
                user_info['email']
            )
        )
        return redirect('authentication:signin')

    if user and not user.is_active:
        messages.error(
            request,
            "User account ({}) found but it has been made inactive.".format(
                user.email,
            )
        )
        return redirect('authentication:signin')
    elif user:
        if token_info.get('id_token'):
            profile = get_profile_safely(user, create_if_necessary=True)
            profile.id_token = token_info['id_token']
            profile.save()
        else:
            # If you signed in with a domain found in settings.ALLOWED_BID
            # then we can't accept NOT getting an id_token
            if user.email.lower().split('@')[1] in settings.ALLOWED_BID:
                messages.error(
                    request,
                    "Staff can't log in without an ID token. "
                    "Means you have to click the Google button if you're "
                    "a member of staff.".format(
                        user_info['email']
                    )
                )
                return redirect('authentication:signin')

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        return redirect(settings.AUTH0_SUCCESS_URL)
    else:
        messages.error(
            request,
            'Email {} authenticated but you are not a vouched Mozillian '
            'on Mozillians.org'.format(
                user_info['email']
            )
        )
        return redirect('authentication:signin')


def default_username(email):
    # Store the username as a base64 encoded sha1 of the email address
    # this protects against data leakage because usernames are often
    # treated as public identifiers (so we can't use the email address).
    return base64.urlsafe_b64encode(
        hashlib.sha1(smart_bytes(email)).digest()
    ).rstrip(b'=')


def get_user(user_info):
    email = user_info['email']

    domain = email.split('@')[-1].lower()
    _allowed_bid = False
    _is_vouched = False

    if domain in settings.ALLOWED_BID:
        # This variable matters later when we have the user
        _allowed_bid = True
    elif is_vouched(email):
        # This variable matters later when we have the user
        _is_vouched = True
    else:
        return

    created = False
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # We have to create the user
            user = User.objects.create(
                email=email,
                username=default_username(email),
            )
            created = True

    if user_info.get('given_name'):
        if user_info['given_name'] != user.first_name:
            user.first_name = user_info['given_name']
            user.save()

    if user_info.get('family_name'):
        if user_info['family_name'] != user.first_name:
            user.last_name = user_info['family_name']
            user.save()

    if _allowed_bid and not created:
        # If you were a contributor before, undo that.
        # This might be the case when we extend settings.ALLOWED_BID
        # with new domains and people with those domains logged
        # in before.
        try:
            # if you were a contributor before, undo that now
            if user.profile.contributor:
                user.profile.contributor = False
                user.profile.save()
        except UserProfile.DoesNotExist:
            pass
    elif _is_vouched:
        # If you existed before and is now not in ALLOWED_BID
        # really make sure you have a UserProfile with
        # .contributor set to True
        try:
            if not user.profile.contributor:
                user.profile.contributor = True
                user.profile.save()
        except UserProfile.DoesNotExist:
            UserProfile.objects.create(
                user=user,
                contributor=True
            )
    return user
