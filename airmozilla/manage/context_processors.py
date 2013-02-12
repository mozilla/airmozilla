from airmozilla.main.models import (
    Approval,
    Event,
    Participant,
    SuggestedEvent
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
    # Uncleared participants badge
    if request.user.has_perm('main.change_participant_others'):
        participants = (
            Participant.objects.filter(cleared=Participant.CLEARED_NO).count()
        )
        if participants > 0:
            context['badges']['part_edit'] = participants

    if request.user.has_perm('main.add_event'):
        suggestions = (
            SuggestedEvent.objects
            .filter(accepted=None)
            .exclude(submitted=None)
            .count()
        )
        if suggestions > 0:
            context['badges']['suggestions'] = suggestions
    return context
