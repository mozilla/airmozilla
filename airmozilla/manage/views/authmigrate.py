from django import forms
from django.shortcuts import render
from django.contrib.auth import get_user_model

from .decorators import superuser_required
from airmozilla.manage.forms import BaseForm
from airmozilla.main.models import (
    Event,
    SuggestedEvent,
    EventEmail,
    EventRevision,
    EventAssignment,
    SuggestedEventComment,
    EventTweet,
    Approval,
    Picture,
    Chapter,
)
from airmozilla.closedcaptions.models import ClosedCaptions, RevOrder
from airmozilla.comments.models import (
    Comment,
    Unsubscription,
    Discussion,
    SuggestedDiscussion,
)
from airmozilla.search.models import (
    LoggedSearch,
    SavedSearch,
)
from airmozilla.starred.models import StarredEvent
from airmozilla.surveys.models import Answer
from airmozilla.uploads.models import Upload

User = get_user_model()


class AuthMigrateForm(BaseForm):
    file = forms.FileField()
    dry_run = forms.BooleanField(required=False)


@superuser_required
def upload(request):  # pragma: no cover
    results = None
    dry_run = False
    if request.method == 'POST':
        form = AuthMigrateForm(request.POST, request.FILES)
        if form.is_valid():
            dry_run = form.cleaned_data['dry_run']
            lines = []
            first = True
            for line in form.cleaned_data['file']:
                if first:
                    first = False
                else:
                    alias, real = line.strip().split(',')
                    lines.append((alias, real))
            if lines:
                results = migrate(lines, dry_run)
    else:
        form = AuthMigrateForm()
    context = {
        'form': form,
        'results': results,
        'dry_run': dry_run,
    }
    return render(request, 'manage/authmigrate_upload.html', context)


def migrate(lines, dry_run=False):
    results = []

    for alias, real in lines:
        try:
            old = User.objects.get(email__iexact=alias)
        except User.DoesNotExist:
            old = None
        try:
            new = User.objects.get(email__iexact=real)
        except User.DoesNotExist:
            new = None

        notes = ''
        if old and not new:
            # Easy, just change this user's email address
            old.email = real
            if not dry_run:
                old.save()
            notes = 'Moved over'
        elif not old and new:
            notes = 'Nothing to do'
        elif not old and not new:
            notes = 'Neither found'
        else:
            assert old and new
            notes = 'Merged'
            notes += '\n({})'.format(
                '\n'.join(merge_user(old, new, dry_run=dry_run))
            )
            if not dry_run:
                old.is_active = False
                old.save()

        results.append({
            'alias': alias,
            'old': old,
            'real': real,
            'is_active': new and new.is_active or None,
            'new': new,
            'notes': notes,
        })

    return results


def merge_user(old, new, dry_run=False):
    things = []

    def migrate(model, key='user', name=None, only_if_in=False):
        if only_if_in:
            if model.objects.filter(**{key: new}).exists():
                model.objects.filter(**{key: old}).delete()
        count = 0
        for instance in model.objects.filter(**{key: old}):
            setattr(instance, key, new)
            if not dry_run:
                instance.save()
            count += 1
        if count > 0:
            things.append('{}{} {}'.format(
                name or model._meta.verbose_name,
                count != 1 and 's' or '',
                count,
            ))

    if old.is_staff:
        new.is_staff = True
        if not dry_run:
            new.save()
        things.append('transferred is_staff')
    if old.is_superuser:
        new.is_superuser = True
        if not dry_run:
            new.save()
        things.append('transferred is_superuser')

    # Groups
    for group in old.groups.all():
        if group not in new.groups.all():
            if not dry_run:
                new.groups.add(group)
            things.append('{} group membership transferred'.format(group.name))

    # Events
    migrate(Event, 'creator')
    migrate(Event, 'modified_user', name='modified event')

    # EventEmail
    migrate(EventEmail)

    # EventRevision
    migrate(EventRevision)

    # SuggestedEventComment
    migrate(SuggestedEventComment)

    # Comments
    migrate(Comment)

    # Discussions
    migrate(Discussion.moderators.through, only_if_in=True)

    # Suggested discussions

    migrate(SuggestedDiscussion.moderators.through, only_if_in=True)

    # Event assignments
    migrate(EventAssignment.users.through, only_if_in=True)

    # Unsubscriptions
    migrate(Unsubscription)

    # SuggestedEvent
    migrate(SuggestedEvent)

    # Closed captions
    migrate(ClosedCaptions, 'created_user')

    # Rev orders
    migrate(RevOrder, 'created_user')

    # EventTweet
    migrate(EventTweet, 'creator')

    # Approval
    migrate(Approval)

    # Picture
    migrate(Picture, 'modified_user')

    # Chapters
    migrate(Chapter)

    # Logged search
    migrate(LoggedSearch)

    # Saved search
    migrate(SavedSearch)

    # Starred events
    migrate(StarredEvent)

    # (survey) Answers
    migrate(Answer)

    # Upload
    migrate(Upload)

    return things
