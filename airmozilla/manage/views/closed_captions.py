import pycaption

from django.shortcuts import render, redirect, get_object_or_404
from django.core.urlresolvers import reverse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone

from .decorators import (
    staff_required,
    permission_required,
    cancel_redirect
)
from airmozilla.base.utils import get_base_url
from airmozilla.main.models import Event, VidlySubmission
from airmozilla.closedcaptions.models import ClosedCaptions
from airmozilla.manage import forms
from airmozilla.manage import vidly


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


class LastTimestampWriter(pycaption.base.BaseWriter):
    def write(self, caption_set):
        lang = caption_set.get_languages()[0]
        captions = caption_set.get_captions(lang)
        last_caption = captions[-1]
        return last_caption.end


@staff_required
@permission_required('closedcaptions.change_closedcaptions')
def event_closed_captions_submit(request, event_id, id):
    event = get_object_or_404(Event, id=event_id)
    closedcaptions = get_object_or_404(ClosedCaptions, event=event, id=id)

    # XXX This might change. Instead of using the same tag as the one
    # being used, we might use a custom one just for the transcription
    # service.
    submission, = VidlySubmission.objects.filter(
        event=event,
        tag=event.template_environment['tag']
    )

    if request.method == 'POST':
        form = forms.SubmitClosedCaptionsForm(request.POST)
        if form.is_valid():
            file_format = form.cleaned_data['file_format']
            base_url = get_base_url(request)
            public_url = base_url + reverse(
                'closedcaptions:download', args=(
                    closedcaptions.filename_hash,
                    closedcaptions.id,
                    event.slug,
                    file_format,
                )
            )

            # Send it in
            vidly.update_media_closed_captions(
                submission.tag,
                submission.url,
                public_url,
                hd=submission.hd,
                notify_url=None  # XXX improve this some day
            )
            if not closedcaptions.submission_info:
                closedcaptions.submission_info = {}
            if not closedcaptions.submission_info.get('submissions'):
                closedcaptions.submission_info['submissions'] = []
            closedcaptions.submission_info['submissions'].append({
                'tag': submission.tag,
                'url': submission.url,
                'public_url': public_url,
                'hd': submission.hd,
                'date': timezone.now().isoformat(),
            })
            closedcaptions.save()
            messages.success(
                request,
                '{} submitted for Vid.ly transcoding'.format(
                    public_url
                )
            )
            return redirect('manage:event_closed_captions', event.id)
    else:
        form = forms.SubmitClosedCaptionsForm()

    content = closedcaptions.file.read()
    reader = pycaption.detect_format(content)
    converter = pycaption.CaptionConverter()
    converter.read(content, reader())
    last_caption = converter.write(LastTimestampWriter()) / 1000000

    context = {
        'form': form,
        'event': closedcaptions.event,
        'closedcaptions': closedcaptions,
        'last_caption': last_caption,
        'submission': submission,
    }
    return render(request, 'manage/event_closed_captions_submit.html', context)
