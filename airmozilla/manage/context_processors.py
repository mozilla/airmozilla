from django.db.models import Q
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
        events = Event.objects.initiated().count()
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
        suggestions = (
            SuggestedEvent.objects
            .filter(accepted=None)
            .exclude(submitted=None)
            .count()
        )
        if suggestions > 0:
            context['badges']['suggestions'] = suggestions
    context['is_superuser'] = request.user.is_superuser
    return context
