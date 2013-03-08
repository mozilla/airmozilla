import datetime
from django import http
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Permission, User
from django.template.defaultfilters import slugify
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import utc
from django.db import transaction
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
from django.contrib.sites.models import RequestSite

from funfactory.urlresolvers import reverse
from airmozilla.main.models import SuggestedEvent, Event
from . import forms


def _increment_slug_if_exists(slug):
    base = slug
    count = 0
    while Event.objects.filter(slug__iexact=slug):
        if not count:
            # add the date
            now = datetime.datetime.utcnow()
            slug = base = slug + now.strftime('-%Y%m%d')
            count = 2
        else:
            slug = base + '-%s' % count
            count += 1
    return slug


@login_required
@transaction.commit_on_success
def start(request):
    data = {}
    if request.method == 'POST':
        form = forms.StartForm(request.POST, user=request.user)
        if form.is_valid():
            slug = slugify(form.cleaned_data['title'])
            slug = _increment_slug_if_exists(slug)
            event = SuggestedEvent.objects.create(
                user=request.user,
                title=form.cleaned_data['title'],
                slug=slug,
            )
            # XXX use next_url() instead?
            url = reverse('suggest:description', args=(event.pk,))
            return redirect(url)
    else:
        form = forms.StartForm(user=request.user)

        data['suggestions'] = (
            SuggestedEvent.objects
            .filter(user=request.user)
            .order_by('modified')
        )
    data['form'] = form
    data['event'] = None

    return render(request, 'suggest/start.html', data)


@login_required
@transaction.commit_on_success
def title(request, id):
    event = get_object_or_404(SuggestedEvent, pk=id)
    if event.user != request.user:
        return http.HttpResponseBadRequest('Not your event')

    if request.method == 'POST':
        form = forms.TitleForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            # XXX use next_url() instead?
            url = reverse('suggest:description', args=(event.pk,))
            return redirect(url)
    else:
        form = forms.TitleForm(instance=event)

    data = {'form': form, 'event': event}
    return render(request, 'suggest/title.html', data)


@login_required
@transaction.commit_on_success
def description(request, id):
    event = get_object_or_404(SuggestedEvent, pk=id)
    if event.user != request.user:
        return http.HttpResponseBadRequest('Not your event')

    if request.method == 'POST':
        form = forms.DescriptionForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            # XXX use next_url() instead?
            url = reverse('suggest:details', args=(event.pk,))
            return redirect(url)
    else:
        form = forms.DescriptionForm(instance=event)

    data = {'form': form, 'event': event}
    return render(request, 'suggest/description.html', data)


@login_required
@transaction.commit_on_success
def details(request, id):
    event = get_object_or_404(SuggestedEvent, pk=id)
    if event.user != request.user:
        return http.HttpResponseBadRequest('Not your event')

    if request.method == 'POST':
        form = forms.DetailsForm(request.POST, instance=event)
        if form.is_valid():
            event = form.save()
            #print "\t", form.cleaned_data
            #event.save()
            #form.save_m2m()
            # XXX use next_url() instead?
            url = reverse('suggest:placeholder', args=(event.pk,))
            return redirect(url)
    else:
        form = forms.DetailsForm(instance=event)

    data = {'form': form, 'event': event}
    return render(request, 'suggest/details.html', data)


@login_required
@transaction.commit_on_success
def placeholder(request, id):
    event = get_object_or_404(SuggestedEvent, pk=id)
    if event.user != request.user:
        return http.HttpResponseBadRequest('Not your event')

    if request.method == 'POST':
        form = forms.PlaceholderForm(
            request.POST,
            request.FILES,
            instance=event
        )
        if form.is_valid():
            event = form.save()
            # XXX use next_url() instead?
            url = reverse('suggest:summary', args=(event.pk,))
            return redirect(url)
    else:
        form = forms.PlaceholderForm()

    data = {'form': form, 'event': event}
    return render(request, 'suggest/placeholder.html', data)


@login_required
@transaction.commit_on_success
def summary(request, id):
    event = get_object_or_404(SuggestedEvent, pk=id)
    if event.user != request.user:
        # it's ok if it's submitted and you have the 'add_event'
        # permission
        if request.user.has_perm('main.add_event'):
            if not event.submitted:
                return http.HttpResponseBadRequest('Not submitted')
        else:
            return http.HttpResponseBadRequest('Not your event')

    if request.method == 'POST':
        if event.submitted:
            event.submitted = None
            event.save()
        else:
            now = datetime.datetime.utcnow().replace(tzinfo=utc)
            event.submitted = now
            event.save()
            _email_about_suggested_event(event, request)
        url = reverse('suggest:summary', args=(event.pk,))
        return redirect(url)

    event.location_time = event.start_time
    return render(request, 'suggest/summary.html', {'event': event})


def _email_about_suggested_event(event, request):
    permission = Permission.objects.get(codename='add_event')
    emails = set()
    for group in permission.group_set.all():
        emails.update([u.email for u in group.user_set.all()])
    # and all superusers
    for superuser in User.objects.filter(is_superuser=True):
        if superuser.email:
            emails.add(superuser.email)
    subject = (
        '[Air Mozilla] New suggested event: %s' % event.title
    )
    base_url = (
        '%s://%s' % (request.is_secure() and 'https' or 'http',
                     RequestSite(request).domain)
    )
    message = render_to_string(
        'suggest/_email_submitted.html',
        {
            'event': event,
            'base_url': base_url,
        }
    )
    assert emails
    email = EmailMessage(
        subject,
        message,
        settings.EMAIL_FROM_ADDRESS,
        emails
    )
    email.send()


@csrf_exempt
@require_POST
@login_required
def delete(request, id):
    event = get_object_or_404(SuggestedEvent, pk=id)
    if event.user != request.user:
        return http.HttpResponseBadRequest('Not your event')
    event.delete()
    return redirect('suggest:start')
