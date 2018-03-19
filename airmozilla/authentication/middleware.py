from django.contrib import auth


class PatchRefreshIDToken(object):
    """This is a very temporary fix.
    It starts with this: https://github.com/mozilla/airmozilla/issues/827
    If the refresh fails, Auth0 sends you back here at the URL:
    /oidc/callback/?error=login_required&error_description=Multif...
    And that triggers a redirect to the harmless /login-failure/ page.
    But you're still logged in! Except that the RefreshIDToken middleware
    insists that it's time to refresh the ID token. So it immediately
    redirects to to /oidc/authenticate/...?prompt=none which immediately
    redirects to back to
    /oidc/callback/?error=login_required&error_description=Multif...
    and so the infinite redirect loop comes around and around.

    In https://github.com/mozilla/mozilla-django-oidc/pull/213 we take a
    serious approach to fixing this.

    In the current state of airmozilla, we're eager to have a much faster
    fix. Hence this middleware.
    Basically, make sure the user gets logged out if the callback URL
    gets requested with a ?error=... query string.
    """

    def process_request(self, request):
        if request.path == '/oidc/callback/' and request.GET.get('error'):
            if request.user.is_authenticated():
                auth.logout(request)
