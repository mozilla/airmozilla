from django.contrib.auth import logout
from django.core.cache import cache
from django.shortcuts import redirect
from django.conf import settings
from django.core.urlresolvers import reverse

from airmozilla.main.models import get_profile_safely
from airmozilla.authentication import auth0


class ValidateIDToken(object):
    """
    For users authenticated with an id_token, we need to check that it's
    still valid. For example, the user could have been blocked (e.g.
    leaving the company) if so we need to ask the user to log in again.
    """

    exception_paths = (
        reverse('authentication:callback'),
    )

    def process_request(self, request):
        if (
            request.method != 'POST' and
            not request.is_ajax() and
            request.user.is_active and
            request.path not in self.exception_paths
        ):
            cache_key = 'renew_id_token:{}'.format(request.user.id)
            if cache.get(cache_key):
                # still valid, we checked recently
                return
            # oh, no we need to check the id_token (and renew it)
            profile = get_profile_safely(request.user)
            if profile and profile.id_token:
                id_token = auth0.renew_id_token(profile.id_token)
                if id_token:
                    assert isinstance(id_token, basestring)
                    profile.id_token = id_token
                    profile.save()
                    cache.set(
                        cache_key,
                        True,
                        settings.RENEW_ID_TOKEN_EXPIRY_SECONDS
                    )
                else:
                    # If that failed, your previous id_token is not valid
                    # and you need to be signed out so you can get a new
                    # one.
                    logout(request)
                    # XXX message?
                    return redirect('authentication:signin')
