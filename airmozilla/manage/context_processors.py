from airmozilla.main.models import Approval, Event, Participant


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
        approvals = Approval.objects.filter(
            group__in=request.user.groups.all(),
            processed=False
        ).count()
        if approvals > 0:
            context['badges']['approvals'] = approvals
    # Uncleared participants badge
    if request.user.has_perm('main.change_participant_others'):
        participants = (
            Participant.objects.filter(cleared=Participant.CLEARED_NO).count()
        )
        if participants > 0:
            context['badges']['part_edit'] = participants
    return context
