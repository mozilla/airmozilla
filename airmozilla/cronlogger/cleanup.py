import datetime

from django.utils import timezone

from airmozilla.cronlogger.models import CronLog


def purge_old(
    delta=datetime.timedelta(days=30 * 6),
    verbose=False,
):
    then = timezone.now() - delta
    qs = CronLog.objects.filter(created__lt=then)
    if verbose:  # pragma: no cover
        print 'Deleting {} old items\n'.format(qs.count())
    qs.delete()
