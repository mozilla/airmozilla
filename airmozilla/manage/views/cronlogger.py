import datetime

from django import http
from django.core.cache import cache
from django.shortcuts import render
from django.db.models import Count

from jsonview.decorators import json_view

from airmozilla.base.utils import dot_dict
from airmozilla.cronlogger.models import CronLog

from .decorators import superuser_required


@superuser_required
def cronlogger_home(request):
    return render(request, 'manage/cronlogger.html')


@superuser_required
@json_view
def cronlogger_data(request):
    context = {}
    values = (
        'job',
        'created',
        'stdout',
        'stderr',
        'exc_type',
        'exc_value',
        'exc_traceback',
        'duration',
    )
    qs = CronLog.objects.all()
    jobs = []
    for each in qs.values('job').annotate(Count('job')):
        jobs.append({
            'text': '%s (%d)' % (each['job'], each['job__count']),
            'value': each['job']
        })
    jobs.sort(key=lambda x: x['value'])
    context['jobs'] = jobs

    if request.GET.get('job'):
        qs = qs.filter(job__exact=request.GET['job'])
    context['count'] = qs.count()
    logs = []
    for log_dict in qs.order_by('-created').values(*values)[:100]:
        log = dot_dict(log_dict)
        log['created'] = log['created'].isoformat()
        logs.append(log)
    context['logs'] = logs

    return context


def cron_pings(request):  # pragma: no cover
    """reveals if the cron_ping management command has recently been fired
    by the cron jobs."""
    if 'LocMemCache' in cache.__class__.__name__:
        return http.HttpResponse(
            "Using LocMemCache so can't test this",
            content_type='text/plain'
        )
    ping = cache.get('cron-ping')
    if not ping:
        return http.HttpResponse(
            'cron-ping has not been executed for at least an hour',
            content_type='text/plain'
        )
    now = datetime.datetime.utcnow()
    return http.HttpResponse(
        'Last cron-ping: %s\n'
        '           Now: %s' % (ping, now),
        content_type='text/plain'
    )
