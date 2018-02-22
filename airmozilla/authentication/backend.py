import hashlib
import logging

from django.contrib.auth import get_user_model
from django_browserid.auth import BrowserIDBackend
from django.core.cache import cache
from django.conf import settings

from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from airmozilla.base.mozillians import is_vouched
from airmozilla.main.models import UserProfile

UserModel = get_user_model()

logger = logging.getLogger('auth')


def hash_email(email):
    return hashlib.md5(email).hexdigest()[:30]


class AirmozillaBrowserIDBackend(BrowserIDBackend):
    """The only difference between this backend and the default
    BrowserIDBackend backend is that this one uses the cache framework
    to remember the user.

    The cache is invalidated by a post_save signal in this app's models.py.
    """

    def get_user(self, user_id):
        if not user_id:
            return None
        cache_key = 'user:%s' % (user_id,)
        user = cache.get(cache_key)
        if user:
            return user
        try:
            user = self.User.objects.get(pk=user_id)
            cache.set(cache_key, user, 60 * 60 * 3)  # 3 hours
            return user
        except self.User.DoesNotExist:
            return None


class AirmozillaOIDCAuthenticationBackend(OIDCAuthenticationBackend):

    def filter_users_by_claims(self, claims):
        users = super(
            AirmozillaOIDCAuthenticationBackend,
            self
        ).filter_users_by_claims(claims)
        # If this returned a set of users, it means the email already
        # exists (got in at some point). If so, do nothing but just
        # return the users.
        if users:
            return users

        # Never heard of this user before!
        # Because we set settings.OIDC_CREATE_USER it won't immediately
        # be created.
        # If we that this user should not be allowed in, return an empty
        # list or empty queryset.
        email = claims.get('email')
        domain = email.split('@')[-1].lower()
        if domain in settings.ALLOWED_BID:
            # You've never signed in before but you have an awesome
            # email domain.
            user = super(
                AirmozillaOIDCAuthenticationBackend,
                self
            ).create_user(claims)
            return [user]

        # A this point, you need to be a vouced mozillian.
        # And if you are you get a "contributor" profile.
        if is_vouched(email):
            user = super(
                AirmozillaOIDCAuthenticationBackend,
                self
            ).create_user(claims)
            UserProfile.objects.create(
                user=user,
                contributor=True
            )
            return [user]

        return UserModel.objects.none()
