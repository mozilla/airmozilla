import logging
from django.conf import settings
from django.contrib import messages

from airmozilla.base.mozillians import is_vouched, BadStatusCodeError
from airmozilla.main.models import UserProfile

from django_browserid.views import Verify
from django_browserid.http import JSONResponse

logger = logging.getLogger('auth')


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
