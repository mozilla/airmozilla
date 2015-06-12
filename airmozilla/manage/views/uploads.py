from django.shortcuts import render, get_object_or_404

from airmozilla.base.utils import paginate
from airmozilla.main.models import Event
from airmozilla.uploads.models import Upload

from .decorators import superuser_required


@superuser_required
def uploads(request):
    event = None
    if request.GET.get('event'):
        event = get_object_or_404(Event, id=request.GET['event'])
    records = (
        Upload.objects
        .select_related('event')
        .order_by('-created')
    )
    if event:
        records = records.filter(event=event)
    paged = paginate(records, request.GET.get('page'), 20)
    context = {
        'paginate': paged,
        'event': event,
    }
    return render(request, 'manage/uploads.html', context)
