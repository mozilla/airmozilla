import datetime

from django.utils import timezone

import cronjobs

from airmozilla.main.models import VidlyTagDomain
from airmozilla.cronlogger.decorators import capture
from airmozilla.main.views.pages import get_vidly_csp_headers


@cronjobs.register
@capture
def refresh_old_vidly_tag_domains():
    minimum = timezone.now() - datetime.timedelta(days=7)
    qs = VidlyTagDomain.objects.filter(modified__lt=minimum)
    for each in qs.order_by('modified')[:10]:
        tag = each.tag
        private = each.private
        print (tag, private, each.modified)
        domain_before = each.domain
        each.delete()
        print 'Domain before: {}'.format(domain_before)
        headers = get_vidly_csp_headers(each.tag, private=each.private)
        print 'New headers: {}'.format(headers)
