import datetime

from django.utils import timezone

import cronjobs

from airmozilla.main.models import VidlyTagDomain
from airmozilla.cronlogger.decorators import capture
from airmozilla.main.views.pages import get_vidly_csp_headers


@cronjobs.register
@capture
def refresh_old_vidly_tag_domains():
    minimum = timezone.now() - datetime.timedelta(days=1)
    qs = VidlyTagDomain.objects.filter(modified__lt=minimum)
    print "There are {} VidlyTagDomains older than {}".format(
        qs.count(),
        minimum,
    )
    print "There are {} VidlyTagDomains newer than {}".format(
        VidlyTagDomain.objects.filter(modified__gte=minimum).count(),
        minimum,
    )
    print ''

    combos = set()
    for each in qs.order_by('modified'):
        tag = each.tag
        private = each.private
        print 'Details: {}'.format({
            'tag': tag,
            'private': private,
            'modified': each.modified
        })
        domain_before = each.domain
        each.delete()
        combo = (each.tag, each.private)
        if combo not in combos:
            print 'Domain before: {}'.format(domain_before)
            headers = get_vidly_csp_headers(each.tag, private=each.private)
            combos.add(combo)
            print 'New headers: {}'.format(headers)
        print ''
