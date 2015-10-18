import hashlib
import logging
from collections import defaultdict
from xml.parsers.expat import ExpatError

from django import http
from django.core.cache import cache
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.db.models import Q, Count
from django.views.decorators.csrf import csrf_exempt
from django.core.urlresolvers import reverse

from jsonview.decorators import json_view
import xmltodict

from airmozilla.base.utils import (
    paginate,
    get_base_url,
    prepare_vidly_video_url,
)
from airmozilla.main.models import Event, VidlySubmission
from airmozilla.manage import forms
from airmozilla.manage import vidly
from airmozilla.manage import archiver

from .decorators import superuser_required


@superuser_required
def vidly_media(request):
    events = Event.objects.filter(
        Q(template__name__contains='Vid.ly') |
        Q(pk__in=VidlySubmission.objects.all()
            .values_list('event_id', flat=True))
    )

    status = request.GET.get('status')
    repeated = request.GET.get('repeated') == 'event'
    repeats = {}

    if status:
        if status not in ('New', 'Processing', 'Finished', 'Error'):
            return http.HttpResponseBadRequest("Invalid 'status' value")

        # make a list of all tags -> events
        _tags = {}
        for event in events:
            environment = event.template_environment or {}
            if not environment.get('tag') or environment.get('tag') == 'None':
                continue
            _tags[environment['tag']] = event.id

        event_ids = []
        for tag in vidly.medialist(status):
            try:
                event_ids.append(_tags[tag])
            except KeyError:
                # it's on vid.ly but not in this database
                logging.debug("Unknown event with tag=%r", tag)

        events = events.filter(id__in=event_ids)
    elif repeated:
        repeats = dict(
            (x['event_id'], x['event__id__count'])
            for x in
            VidlySubmission.objects
            .values('event_id')
            .annotate(Count('event__id'))
            .filter(event__id__count__gt=1)
        )
        events = Event.objects.filter(id__in=repeats.keys())

    def get_repeats(event):
        return repeats[event.id]

    events = events.order_by('-start_time')
    events = events.select_related('template')
    paged = paginate(events, request.GET.get('page'), 15)

    submissions = defaultdict(list)
    for submission in VidlySubmission.objects.filter(event__in=paged):
        submissions[submission.event_id].append(submission)

    vidly_resubmit_form = forms.VidlyResubmitForm()
    context = {
        'paginate': paged,
        'status': status,
        'vidly_resubmit_form': vidly_resubmit_form,
        'repeated': repeated,
        'get_repeats': get_repeats,
        'submissions': submissions,
    }
    return render(request, 'manage/vidly_media.html', context)


@superuser_required
@json_view
def vidly_media_status(request):
    context = {}
    if request.GET.get('tag'):
        tag = request.GET.get('tag')
    else:
        if not request.GET.get('id'):
            return http.HttpResponseBadRequest("No 'id'")
        event = get_object_or_404(Event, pk=request.GET['id'])
        environment = event.template_environment or {}

        if not environment.get('tag') or environment.get('tag') == 'None':
            # perhaps it has a VidlySubmission anyway
            submissions = (
                VidlySubmission.objects
                .exclude(tag__isnull=True)
                .filter(event=event).order_by('-submission_time')
            )
            for submission in submissions[:1]:
                environment = {'tag': submission.tag}
                break
            else:
                return {}
        tag = environment['tag']

    cache_key = 'vidly-query-{md5}'.format(
        md5=hashlib.md5(tag.encode('utf8')).hexdigest().strip())
    force = request.GET.get('refresh', False)
    if force:
        results = None  # force a refresh
    else:
        results = cache.get(cache_key)
    if not results:
        results = vidly.query(tag).get(tag, {})
        expires = 60
        # if it's healthy we might as well cache a bit
        # longer because this is potentially used a lot
        if results.get('Status') == 'Finished':
            expires = 60 * 60
        if results:
            cache.set(cache_key, results, expires)

    context['status'] = results.get('Status')
    return context


@superuser_required
@json_view
def vidly_media_info(request):

    def as_fields(result):
        return [
            {'key': a, 'value': b}
            for (a, b)
            in sorted(result.items())
        ]

    if not request.GET.get('id'):
        return http.HttpResponseBadRequest("No 'id'")
    event = get_object_or_404(Event, pk=request.GET['id'])
    environment = event.template_environment or {}

    if not environment.get('tag') or environment.get('tag') == 'None':
        # perhaps it has a VidlySubmission anyway
        submissions = (
            VidlySubmission.objects
            .exclude(tag__isnull=True)
            .filter(event=event).order_by('-submission_time')
        )
        for submission in submissions[:1]:
            environment = {'tag': submission.tag}
            break

    if not environment.get('tag') or environment.get('tag') == 'None':
        return {'fields': as_fields({
            '*Note*': 'Not a valid tag in template',
            '*Template contents*': unicode(environment),
        })}
    else:
        tag = environment['tag']
        cache_key = 'vidly-query-%s' % tag
        force = request.GET.get('refresh', False)
        if force:
            results = None  # force a refresh
        else:
            results = cache.get(cache_key)
        if not results:
            all_results = vidly.query(tag)
            if tag not in all_results:
                return {
                    'ERRORS': ['Tag (%s) not found in Vid.ly' % tag]
                }
            results = all_results[tag]
            cache.set(cache_key, results, 60)

    data = {'fields': as_fields(results)}
    is_hd = results.get('IsHD', False)
    if is_hd == 'false':
        is_hd = False

    data['past_submission'] = {
        'url': results['SourceFile'],
        'email': results['UserEmail'],
        'hd': bool(is_hd),
        'token_protection': event.privacy != Event.PRIVACY_PUBLIC,
    }
    if request.GET.get('past_submission_info'):
        qs = (
            VidlySubmission.objects
            .filter(event=event)
            .order_by('-submission_time')
        )
        for submission in qs[:1]:
            if event.privacy != Event.PRIVACY_PUBLIC:
                # forced
                token_protection = True
            else:
                # whatever it was before
                token_protection = submission.token_protection
            data['past_submission'] = {
                'url': submission.url,
                'email': submission.email,
                'hd': submission.hd,
                'token_protection': token_protection,
            }

    return data


@require_POST
@superuser_required
def vidly_media_resubmit(request):
    if request.POST.get('cancel'):
        return redirect(reverse('manage:vidly_media') + '?status=Error')

    form = forms.VidlyResubmitForm(data=request.POST)
    if not form.is_valid():
        return http.HttpResponse(str(form.errors))
    event = get_object_or_404(Event, pk=form.cleaned_data['id'])
    environment = event.template_environment or {}
    if not environment.get('tag') or environment.get('tag') == 'None':
        raise ValueError("Not a valid tag in template")

    if event.privacy != Event.PRIVACY_PUBLIC:
        token_protection = True  # no choice
    else:
        token_protection = form.cleaned_data['token_protection']

    base_url = get_base_url(request)
    webhook_url = base_url + reverse('manage:vidly_media_webhook')

    old_tag = environment['tag']
    url = prepare_vidly_video_url(form.cleaned_data['url'])
    shortcode, error = vidly.add_media(
        url=url,
        hd=form.cleaned_data['hd'],
        token_protection=token_protection,
        notify_url=webhook_url,
    )
    VidlySubmission.objects.create(
        event=event,
        url=url,
        token_protection=token_protection,
        hd=form.cleaned_data['hd'],
        tag=shortcode,
        submission_error=error
    )

    if error:
        messages.warning(
            request,
            "Media could not be re-submitted:\n<br>\n%s" % error
        )
    else:
        messages.success(
            request,
            "Event re-submitted to use tag '%s'" % shortcode
        )
        vidly.delete_media(old_tag)
        event.template_environment['tag'] = shortcode
        event.save()

        cache_key = 'vidly-query-%s' % old_tag
        cache.delete(cache_key)

    return redirect(reverse('manage:vidly_media') + '?status=Error')


# Note that this view is publically available.
# That means we can't trust the content but we can take it as a hint.
@csrf_exempt
@require_POST
def vidly_media_webhook(request):
    if not request.POST.get('xml'):
        return http.HttpResponseBadRequest("no 'xml'")

    # We can expect three pieces of XML.
    # 1) That the media was submitted
    # https://bug1135808.bugzilla.mozilla.org/attachment.cgi?id=8568143
    # 2) That the media failed processing
    # https://bug1135808.bugzilla.mozilla.org/attachment.cgi?id=8568190
    # 3) That the media succeeded processing
    # https://bug1135808.bugzilla.mozilla.org/attachment.cgi?id=8568149
    #
    # If it's case number 1, just ignore it and do nothing.
    # If it's case number 2 or number 3, take it as a hint you can't trust
    # and kick off the auto-archive procedure.
    xml_string = request.POST['xml'].strip()

    try:
        struct = xmltodict.parse(xml_string)
    except ExpatError:
        return http.HttpResponseBadRequest("Bad 'xml'")

    try:
        struct['Response']['Result']['Task']
        archiver.auto_archive()
    except KeyError:
        # If it doesn't have a "Result" or "Task", it was just a notification
        # that the media was added.
        pass

    return http.HttpResponse('OK\n')


@superuser_required
def vidly_media_timings(request):
    context = {
    }
    return render(request, 'manage/vidly_media_timings.html', context)


@superuser_required
@json_view
def vidly_media_timings_data(request):
    points = VidlySubmission.get_points(100)
    slope = VidlySubmission.get_least_square_slope(points=points)
    context = {
        'points': points,
        'slope': slope,
    }
    return context
