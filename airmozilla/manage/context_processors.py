import datetime

from django.db.models import Q
from django.utils import timezone

from airmozilla.main.models import (
    Approval,
    Event,
    SuggestedEvent,
    EventTweet
)


def badges(request):
    if not request.path.startswith('/manage/'):
        return {}
    context = {'badges': {}}
    # Event manager badge for unprocessed events
    if request.user.has_perm('main.change_event_others'):
        events = Event.objects.filter(
            Q(status=Event.STATUS_SUBMITTED) |
            Q(approval__approved=False) |
            Q(approval__processed=False)
        ).exclude(
            status=Event.STATUS_INITIATED
        ).distinct().count()
        if events > 0:
            context['badges']['events'] = events
    # Approval inbox badge
    if request.user.has_perm('main.change_approval'):
        approvals = (Approval.objects.filter(
            group__in=request.user.groups.all(),
            processed=False)
            .exclude(event__status=Event.STATUS_REMOVED)
            .count()
        )
        if approvals > 0:
            context['badges']['approvals'] = approvals

    # Unsent tweets
    if request.user.has_perm('main.change'):
        tweets = (
            EventTweet.objects.filter(
                Q(sent_date__isnull=True) | Q(error__isnull=False)
            )
            .count()
        )
        if tweets:
            context['badges']['tweets'] = tweets

    if request.user.has_perm('main.add_event'):
        now = timezone.now()
        then = now - datetime.timedelta(days=30)
        suggestions = (
            SuggestedEvent.objects
            .filter(accepted=None)
            .filter(first_submitted__gte=then)
            .exclude(first_submitted=None)
            .count()
        )

        if suggestions > 0:
            context['badges']['suggestions'] = suggestions
    context['is_superuser'] = request.user.is_superuser
    return context
