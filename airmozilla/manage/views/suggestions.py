import datetime

from django import http
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.core.urlresolvers import reverse

from airmozilla.main.models import (
    Event,
    Template,
    SuggestedEvent,
    SuggestedEventComment,
    LocationDefaultEnvironment,
    Approval,
)
from airmozilla.manage import forms
from airmozilla.manage import sending
from airmozilla.comments.models import Discussion, SuggestedDiscussion

from .decorators import staff_required, permission_required


@staff_required
@permission_required('main.add_event')
def suggestions(request):
    context = {}
    events = (
        SuggestedEvent.objects
        .filter(accepted=None)
        .exclude(first_submitted=None)
        .order_by('submitted')
    )
    context['include_old'] = request.GET.get('include_old')
    if not context['include_old']:
        now = timezone.now()
        then = now - datetime.timedelta(days=30)
        events = events.filter(first_submitted__gte=then)

    context['events'] = events
    return render(request, 'manage/suggestions.html', context)


@staff_required
@permission_required('main.add_event')
@transaction.atomic
def suggestion_review(request, id):
    event = get_object_or_404(SuggestedEvent, pk=id)
    real_event_form = None
    comment_form = forms.SuggestedEventCommentForm()

    if request.method == 'POST':

        if request.POST.get('unbounce'):
            event.submitted = timezone.now()
            event.save()
            return redirect('manage:suggestion_review', event.pk)

        if not event.submitted:
            return http.HttpResponseBadRequest('Not submitted')

        form = forms.AcceptSuggestedEventForm(
            request.POST,
            instance=event,
        )

        if request.POST.get('save_comment'):
            comment_form = forms.SuggestedEventCommentForm(data=request.POST)
            if comment_form.is_valid():
                comment = SuggestedEventComment.objects.create(
                    comment=comment_form.cleaned_data['comment'].strip(),
                    user=request.user,
                    suggested_event=event
                )
                sending.email_about_suggestion_comment(
                    comment,
                    request.user,
                    request
                )
                messages.info(
                    request,
                    'Comment added and %s notified.' % comment.user.email
                )
                return redirect('manage:suggestion_review', event.pk)

        reject = request.POST.get('reject')
        if reject:
            form.fields['review_comments'].required = True

        if not request.POST.get('save_comment') and form.is_valid():
            form.save()
            if reject:
                event.submitted = None
                event.status = SuggestedEvent.STATUS_REJECTED
                event.save()
                sending.email_about_rejected_suggestion(
                    event,
                    request.user,
                    request
                )
                messages.info(
                    request,
                    'Suggested event bounced back and %s has been emailed'
                    % (event.user.email,)
                )
                url = reverse('manage:suggestions')
                return redirect(url)
            else:
                dict_event = {
                    'title': event.title,
                    'description': event.description,
                    'short_description': event.short_description,
                    'start_time': event.start_time,
                    'timezone': event.location.timezone,
                    'location': event.location.pk,
                    'channels': [x.pk for x in event.channels.all()],
                    'call_info': event.call_info,
                    'privacy': event.privacy,
                    'estimated_duration': event.estimated_duration,
                    'topics': [x.pk for x in event.topics.all()],
                }
                real_event_form = forms.EventRequestForm(
                    data=dict_event,
                )
                real_event_form.fields['placeholder_img'].required = False
                if real_event_form.is_valid():
                    real = real_event_form.save(commit=False)
                    real.placeholder_img = event.placeholder_img
                    real.picture = event.picture
                    real.slug = event.slug
                    real.additional_links = event.additional_links
                    real.remote_presenters = event.remote_presenters
                    real.creator = request.user
                    real.status = Event.STATUS_SUBMITTED
                    # perhaps we have a default location template
                    # environment
                    if real.location:
                        try:
                            default = (
                                LocationDefaultEnvironment.objects
                                .get(
                                    location=real.location,
                                    privacy=real.privacy
                                )
                            )
                            real.template = default.template
                            real.template_environment = (
                                default.template_environment
                            )
                        except LocationDefaultEnvironment.DoesNotExist:
                            pass
                    real.save()
                    [real.tags.add(x) for x in event.tags.all()]
                    [real.channels.add(x) for x in event.channels.all()]
                    [real.topics.add(x) for x in event.topics.all()]
                    event.accepted = real
                    event.save()

                    # create the necessary approval bits
                    if event.privacy == Event.PRIVACY_PUBLIC:
                        groups = []
                        for topic in real.topics.filter(is_active=True):
                            for group in topic.groups.all():
                                if group not in groups:
                                    groups.append(group)
                        for group in groups:
                            Approval.objects.create(
                                event=real,
                                group=group,
                            )
                            sending.email_about_approval_requested(
                                real,
                                group,
                                request
                            )
                    try:
                        discussion = SuggestedDiscussion.objects.get(
                            event=event,
                            enabled=True
                        )
                        real_discussion = Discussion.objects.create(
                            enabled=True,
                            event=real,
                            notify_all=discussion.notify_all,
                            moderate_all=discussion.moderate_all,
                        )
                        for moderator in discussion.moderators.all():
                            real_discussion.moderators.add(moderator)
                    except SuggestedDiscussion.DoesNotExist:
                        pass

                    # if this is a popcorn event, and there is a default
                    # popcorn template, then assign that
                    if real.popcorn_url:
                        real.status = Event.STATUS_SCHEDULED
                        templates = Template.objects.filter(
                            default_popcorn_template=True
                        )
                        for template in templates[:1]:
                            real.template = template
                        real.save()

                    sending.email_about_accepted_suggestion(
                        event,
                        real,
                        request
                    )
                    messages.info(
                        request,
                        'New event created from suggestion.'
                    )
                    if real.popcorn_url or not event.upcoming:
                        url = reverse('manage:events')
                    else:
                        url = reverse('manage:event_edit', args=(real.pk,))
                    return redirect(url)
                else:
                    print real_event_form.errors
    else:
        form = forms.AcceptSuggestedEventForm(instance=event)

    # we don't need the label for this form layout
    comment_form.fields['comment'].label = ''

    comments = (
        SuggestedEventComment.objects
        .filter(suggested_event=event)
        .select_related('user')
        .order_by('created')
    )

    discussion = None
    for each in SuggestedDiscussion.objects.filter(event=event):
        discussion = each

    context = {
        'event': event,
        'form': form,
        'real_event_form': real_event_form,
        'comment_form': comment_form,
        'comments': comments,
        'discussion': discussion,
    }
    return render(request, 'manage/suggestion_review.html', context)
