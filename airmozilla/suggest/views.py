import datetime

from django import http
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.timezone import utc, make_naive
from django.db import transaction
from django.conf import settings

import requests
import pytz
from funfactory.urlresolvers import reverse
from slugify import slugify

from airmozilla.main.models import (
    SuggestedEvent,
    Event,
    Channel,
    SuggestedEventComment,
    Location
)
from airmozilla.uploads.models import Upload
from airmozilla.comments.models import SuggestedDiscussion
from airmozilla.base.utils import tz_apply, json_view

from . import utils
from . import forms
from . import sending


def _increment_slug_if_exists(slug):
    base = slug
    count = 2

    def exists(slug):
        return (
            Event.objects.filter(slug__iexact=slug)
            or
            SuggestedEvent.objects.filter(slug__iexact=slug)
        )

    while exists(slug):
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
            slug = slugify(form.cleaned_data['title']).lower()
            slug = _increment_slug_if_exists(slug)
            upcoming = False
            event_type = form.cleaned_data['event_type']
            if event_type == 'upcoming':
                upcoming = True
            event = SuggestedEvent.objects.create(
                user=request.user,
                title=form.cleaned_data['title'],
                upcoming=upcoming,
                slug=slug,
            )
            if not event.upcoming:
                cyberspace, __ = Location.objects.get_or_create(
                    name='Cyberspace',
                    timezone='UTC'
                )
                event.location = cyberspace
                now = datetime.datetime.utcnow().replace(tzinfo=utc)
                event.start_time = now
                event.save()
            event.channels.add(
                Channel.objects.get(slug=settings.DEFAULT_CHANNEL_SLUG)
            )
            # XXX use next_url() instead?
            if event.upcoming:
                url = reverse('suggest:description', args=(event.pk,))
            elif event_type == 'popcorn':
                # this is a hack but it works well
                event.popcorn_url = 'https://'
                event.save()
                url = reverse('suggest:popcorn', args=(event.pk,))
            else:
                request.session['active_suggested_event'] = event.pk
                if request.session.get('active_event'):
                    del request.session['active_event']
                url = reverse('uploads:upload')
            return redirect(url)
    else:
        initial = {
            'event_type': 'upcoming'
        }
        if request.GET.get('upload'):
            try:
                upload = Upload.objects.get(
                    pk=request.GET['upload'],
                    user=request.user
                )
                # is that upload used by some other suggested event
                # in progress?
                try:
                    suggested_event = SuggestedEvent.objects.get(
                        upload=upload
                    )
                    # that's bad!
                    messages.warning(
                        request,
                        'The file upload you selected belongs to a requested '
                        'event with the title: %s' % suggested_event.title
                    )
                    return redirect('uploads:home')
                except SuggestedEvent.DoesNotExist:
                    pass

                initial['event_type'] = 'pre-recorded'
                request.session['active_upload'] = upload.pk
            except Upload.DoesNotExist:
                pass

        form = forms.StartForm(user=request.user, initial=initial)

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
            event = form.save()
            # XXX use next_url() instead?
            url = reverse('suggest:description', args=(event.pk,))
            return redirect(url)
    else:
        form = forms.TitleForm(instance=event)

    data = {'form': form, 'event': event}
    return render(request, 'suggest/title.html', data)


@login_required
@transaction.commit_on_success
def choose_file(request, id):
    event = get_object_or_404(SuggestedEvent, pk=id)
    if event.user != request.user:
        return http.HttpResponseBadRequest('Not your event')
    if event.upcoming:
        return redirect(reverse('suggest:description', args=(event.pk,)))

    if request.method == 'POST':
        form = forms.ChooseFileForm(
            request.POST,
            user=request.user,
            instance=event
        )
        if form.is_valid():
            event = form.save()
            event.upload.suggested_event = event
            event.upload.save()
            # did any *other* upload belong to this suggested event?
            other_uploads = (
                Upload.objects
                .filter(suggested_event=event)
                .exclude(pk=event.upload.pk)
            )
            for upload in other_uploads:
                upload.suggested_event = None
                upload.save()
            if request.session.get('active_suggested_event'):
                del request.session['active_suggested_event']
            # XXX use next_url() instead?
            url = reverse('suggest:description', args=(event.pk,))
            return redirect(url)
    else:
        initial = {}
        if request.GET.get('upload'):
            try:
                upload = Upload.objects.get(
                    pk=request.GET['upload'],
                    user=request.user
                )
                initial['upload'] = upload.pk
            except Upload.DoesNotExist:
                pass
        form = forms.ChooseFileForm(
            user=request.user,
            instance=event,
            initial=initial
        )

    data = {'form': form, 'event': event}
    return render(request, 'suggest/file.html', data)


@login_required
@transaction.commit_on_success
def popcorn(request, id):
    event = get_object_or_404(SuggestedEvent, pk=id)
    if event.user != request.user:
        return http.HttpResponseBadRequest('Not your event')
    if event.upcoming:
        return redirect(reverse('suggest:description', args=(event.pk,)))

    if request.method == 'POST':
        form = forms.PopcornForm(
            request.POST,
            instance=event
        )
        if form.is_valid():
            event = form.save()
            image_url = utils.find_open_graph_image_url(event.popcorn_url)
            if image_url:
                from django.core.files.uploadedfile import InMemoryUploadedFile
                import os
                from StringIO import StringIO
                image_content = requests.get(image_url).content
                buf = StringIO(image_content)
                # Seek to the end of the stream, so we can get its
                # length with `buf.tell()`
                buf.seek(0, 2)
                file = InMemoryUploadedFile(
                    buf,
                    "image",
                    os.path.basename(image_url),
                    None,
                    buf.tell(),
                    None
                )
                event.placeholder_img = file
                event.save()
            # XXX use next_url() instead?
            url = reverse('suggest:description', args=(event.pk,))
            return redirect(url)
    else:
        initial = {}
        form = forms.PopcornForm(
            instance=event,
            initial=initial
        )

    data = {'form': form, 'event': event}
    return render(request, 'suggest/popcorn.html', data)


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

    try:
        discussion = SuggestedDiscussion.objects.get(event=event)
    except SuggestedDiscussion.DoesNotExist:
        discussion = None

    if request.method == 'POST':
        form = forms.DetailsForm(request.POST, instance=event)
        if form.is_valid():
            event = form.save()
            # the start_time comes to us as a string, e.g. '2014-01-01
            # 12:00:00' and that'll be converted into '2014-01-01
            # 12:00:00 tzinfo=UTC' automatically. But that's not what we want
            # so we change it first.
            event.start_time = tz_apply(
                event.start_time,
                pytz.timezone(event.location.timezone)
            )
            event.save()
            next_url = reverse('suggest:placeholder', args=(event.pk,))

            if form.cleaned_data['enable_discussion']:
                if discussion:
                    # make sure it's enabled
                    discussion.enabled = True
                    discussion.moderate_all = (
                        event.privacy != Event.PRIVACY_COMPANY
                    )
                    discussion.save()
                else:
                    discussion = SuggestedDiscussion.objects.create(
                        event=event,
                        enabled=True,
                        notify_all=True,
                        moderate_all=event.privacy != Event.PRIVACY_COMPANY
                    )
                if request.user not in discussion.moderators.all():
                    discussion.moderators.add(request.user)

                next_url = reverse('suggest:discussion', args=(event.pk,))

            elif SuggestedDiscussion.objects.filter(event=event):
                discussion = SuggestedDiscussion.objects.get(event=event)
                discussion.enabled = False
                discussion.save()

            return redirect(next_url)
    else:
        if event.location and event.start_time:
            # Because the modelform is going present our user
            # without input widgets' that are datetimes in
            # naive format, when it does this is does so using the
            # settings.TIME_ZONE and when saved it applies the
            # settings.TIME_ZONE back again.
            # Normally in Django templates, this is solved with
            #  {% timezone "Europe/Paris" %}
            #    {{ form.as_p }}
            #  {% endtimezone %}
            # But that's not going to work when working with jinja
            # so we do it manually from the view code.
            event.start_time = make_naive(
                event.start_time,
                pytz.timezone(event.location.timezone)
            )
        initial = {'enable_discussion': True}
        form = forms.DetailsForm(instance=event, initial=initial)

    data = {'form': form, 'event': event}
    return render(request, 'suggest/details.html', data)


@login_required
@transaction.commit_on_success
def discussion(request, id):
    event = get_object_or_404(SuggestedEvent, pk=id)
    if event.user != request.user:
        return http.HttpResponseBadRequest('Not your event')

    discussion = SuggestedDiscussion.objects.get(event=event)

    if request.method == 'POST':
        form = forms.DiscussionForm(request.POST, instance=discussion)
        if form.is_valid():
            discussion = form.save()
            if event.privacy != Event.PRIVACY_COMPANY:
                discussion.moderate_all = True
                discussion.save()
            discussion.moderators.clear()
            for email in form.cleaned_data['emails']:
                try:
                    user = User.objects.get(email__iexact=email)
                except User.DoesNotExist:
                    user = User.objects.create(
                        username=email.split('@')[0],
                        email=email
                    )
                    user.set_unusable_password()
                    user.save()
                discussion.moderators.add(user)
            url = reverse('suggest:placeholder', args=(event.pk,))
            return redirect(url)
    else:
        emails = [request.user.email]
        for moderator in discussion.moderators.all():
            if moderator.email not in emails:
                emails.append(moderator.email)
        initial = {'emails': ', '.join(emails)}
        form = forms.DiscussionForm(instance=discussion, initial=initial)

    context = {'event': event, 'form': form, 'discussion': discussion}
    return render(request, 'suggest/discussion.html', context)


@login_required
@json_view
def autocomplete_emails(request):
    if 'q' not in request.GET:
        return http.HttpResponseBadRequest('Missing q')
    q = request.GET.get('q', '').strip()
    emails = []

    if len(q) > 1:
        users = (
            User.objects
            .filter(email__istartswith=q)
            .exclude(email__isnull=True)
        )
        for user in users.order_by('email'):
            if user.email not in emails:
                emails.append(user.email)
    if not emails:
        if utils.is_valid_email(q):
            emails.append(q)
        elif utils.is_valid_email('%s@mozilla.com' % q):
            emails.append('%s@mozilla.com' % q)
    return {'emails': emails}


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

    comment_form = forms.SuggestedEventCommentForm()

    if request.method == 'POST':
        if request.POST.get('save_comment'):
            comment_form = forms.SuggestedEventCommentForm(data=request.POST)
            if comment_form.is_valid():
                comment = SuggestedEventComment.objects.create(
                    comment=comment_form.cleaned_data['comment'].strip(),
                    user=request.user,
                    suggested_event=event
                )
                if event.submitted:
                    sending.email_about_suggested_event_comment(
                        comment,
                        request
                    )
                    messages.info(
                        request,
                        'Comment added and producers notified by email.'
                    )
                else:
                    messages.info(
                        request,
                        'Comment added but not emailed to producers because '
                        'the event is not submitted.'
                    )
                return redirect('suggest:summary', event.pk)
        else:
            if event.submitted:
                event.submitted = None
                event.save()
            else:
                now = datetime.datetime.utcnow().replace(tzinfo=utc)
                event.submitted = now
                if not event.first_submitted:
                    event.first_submitted = now
                event.save()
                sending.email_about_suggested_event(event, request)
            url = reverse('suggest:summary', args=(event.pk,))
            return redirect(url)

    # we don't need the label for this form layout
    comment_form.fields['comment'].label = ''

    comments = (
        SuggestedEventComment.objects
        .filter(suggested_event=event)
        .select_related('User')
        .order_by('created')
    )

    discussion = None
    for each in SuggestedDiscussion.objects.filter(event=event):
        discussion = each

    context = {
        'event': event,
        'comment_form': comment_form,
        'comments': comments,
        'discussion': discussion,
    }
    return render(request, 'suggest/summary.html', context)


@csrf_exempt
@require_POST
@login_required
def delete(request, id):
    event = get_object_or_404(SuggestedEvent, pk=id)
    if event.user != request.user:
        return http.HttpResponseBadRequest('Not your event')
    event.delete()
    return redirect('suggest:start')
