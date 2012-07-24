from airmozilla.main.models import Approval, Event, Participant

def badges(request):
    if not request.path.startswith('/manage/'):
        return {}
    context = {'badges': {}}
    # Event manager badge for unprocessed events
    events = Event.objects.initiated().count()
    if events > 0:
        context['badges']['events'] = events
    # Approval inbox badge
    approvals = Approval.objects.filter(group__in=request.user.groups.all(),
                                        processed=False).count()
    if approvals > 0:
        context['badges']['approvals'] = approvals
    # Uncleared participants badge
    participants = (Participant.objects.filter(cleared=Participant.CLEARED_NO)
                                       .count())
    if participants > 0:
        context['badges']['part_edit'] = participants
    return context
