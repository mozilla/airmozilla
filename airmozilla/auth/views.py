import logging
from django.conf import settings
from django.contrib import messages

from .mozillians import is_vouched, BadStatusCodeError
from airmozilla.main.models import UserProfile

from django_browserid.views import Verify

logger = logging.getLogger('auth')


class CustomBrowserIDVerify(Verify):

    def login_success(self):
        """the user passed the BrowserID hurdle, but do they have a valid
        email address or vouched for in Mozillians"""
        domain = self.user.email.split('@')[-1]
        try:
            if domain in settings.ALLOWED_BID:
                # awesome!
                pass
            elif is_vouched(self.user.email):
                try:
                    profile = self.user.get_profile()
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
                return super(CustomBrowserIDVerify, self).login_failure()
        except BadStatusCodeError:
            logger.error('Unable to call out to mozillians', exc_info=True)
            messages.error(
                self.request,
                'Email {0} authenticated but unable to connect to '
                'Mozillians to see if are vouched. '
                .format(self.user.email)
            )
            return super(CustomBrowserIDVerify, self).login_failure()

        return super(CustomBrowserIDVerify, self).login_success()
