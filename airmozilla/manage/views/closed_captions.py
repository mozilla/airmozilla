from django.shortcuts import render, redirect, get_object_or_404
from django.core.urlresolvers import reverse
from django.views.decorators.http import require_POST

from .decorators import (
    staff_required,
    permission_required,
    cancel_redirect
)
from airmozilla.main.models import Event
from airmozilla.closedcaptions.models import ClosedCaptions
from airmozilla.manage import forms


@staff_required
@permission_required('closedcaptions.add_closedcaptions')
@cancel_redirect(
    lambda r, event_id: reverse('manage:event_edit', args=(event_id,))
)
def event_closed_captions(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        form = forms.UploadClosedCaptionsForm(request.POST, request.FILES)
        if form.is_valid():
            file_info = {
                'name': form.cleaned_data['file'].name,
                'size': form.cleaned_data['file'].size,
                'content_type': form.cleaned_data['file'].content_type,
            }
            ClosedCaptions.objects.create(
                event=event,
                created_user=request.user,
                file_info=file_info,
                file=form.cleaned_data['file'],
            )
            return redirect(reverse(
                'manage:event_closed_captions',
                args=(event.id,)
            ))
    else:
        form = forms.UploadClosedCaptionsForm()

    closedcaptions = ClosedCaptions.objects.filter(event=event)
    context = {
        'event': event,
        'form': form,
        'closedcaptions': closedcaptions.order_by('created'),
    }
    return render(request, 'manage/event_closed_captions.html', context)


@staff_required
@permission_required('closedcaptions.delete_closedcaptions')
@require_POST
def event_closed_captions_delete(request, event_id, id):
    event = get_object_or_404(Event, id=event_id)
    closedcaptions = get_object_or_404(ClosedCaptions, event=event, id=id)
    closedcaptions.delete()
    return redirect('manage:event_closed_captions', event.id)
