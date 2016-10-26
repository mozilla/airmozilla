import os

import pycaption
import requests

from django import http
from django.shortcuts import render, redirect, get_object_or_404
from django.core.urlresolvers import reverse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from django.db import transaction

from .decorators import (
    staff_required,
    permission_required,
    cancel_redirect
)
from airmozilla.base.utils import get_base_url
from airmozilla.main.models import Event, VidlySubmission
from airmozilla.closedcaptions.models import (
    ClosedCaptions,
    ClosedCaptionsTranscript,
    RevInput,
    RevOrder,
)
from airmozilla.manage import forms
from airmozilla.manage import vidly
from airmozilla.base import rev


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
    transcript_closedcaptions = None
    for connection in ClosedCaptionsTranscript.objects.filter(event=event):
        transcript_closedcaptions = connection.closedcaptions
    context = {
        'event': event,
        'form': form,
        'closedcaptions': closedcaptions.order_by('created'),
        'transcript_closedcaptions': transcript_closedcaptions,
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
@cancel_redirect(
    lambda r, event_id, id: reverse('manage:event_closed_captions', args=(
        event_id,
    ))
)
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


@staff_required
@cancel_redirect(
    lambda r, event_id, id: reverse('manage:event_closed_captions', args=(
        event_id,
    ))
)
@permission_required('closedcaptions.change_closedcaptions')
def event_closed_captions_transcript(request, event_id, id):
    event = get_object_or_404(Event, id=event_id)
    closedcaptions = get_object_or_404(ClosedCaptions, event=event, id=id)

    if request.method == 'POST':
        # make sure the transcript is current
        closedcaptions.set_transcript_from_file()
        closedcaptions.save()

        ClosedCaptionsTranscript.objects.filter(event=event).delete()
        ClosedCaptionsTranscript.objects.create(
            event=event,
            closedcaptions=closedcaptions
        )
        event.transcript = closedcaptions.get_plaintext_transcript()
        event.save()

        messages.success(
            request,
            'Closed Captions file chosen as event transcript.'
        )
        return redirect('manage:event_closed_captions', event.id)

    if not closedcaptions.transcript:
        closedcaptions.set_transcript_from_file()
        closedcaptions.save()
    else:
        # Always set the latest
        closedcaptions.set_transcript_from_file()

    context = {
        # 'form': form,
        'event': closedcaptions.event,
        'closedcaptions': closedcaptions,
    }
    return render(
        request,
        'manage/event_closed_captions_transcript.html',
        context
    )


@staff_required
@permission_required('closedcaptions.change_closedcaptions')
def event_rev_orders(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    rev_orders = RevOrder.objects.filter(event=event).order_by('created')
    context = {
        'event': event,
        'rev_orders': rev_orders,
    }
    return render(
        request,
        'manage/event_rev_orders.html',
        context
    )


@staff_required
@cancel_redirect(
    lambda r, event_id: reverse('manage:event_closed_captions', args=(
        event_id,
    ))
)
@permission_required('closedcaptions.change_closedcaptions')
@transaction.atomic
def new_event_rev_order(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        form = forms.RevInputForm(request.POST)
        if form.is_valid():
            rev_input = RevInput.objects.create(
                url=form.cleaned_data['url'],
                content_type=form.cleaned_data['content_type'],
                filename=form.cleaned_data['filename'],
            )
            uri = rev.input_order(
                rev_input.url,
                filename=rev_input.filename,
                content_type=rev_input.content_type,
            )
            rev_input.uri = uri
            rev_input.save()

            rev_order = RevOrder.objects.create(
                event=event,
                input=rev_input,
                created_user=request.user,
                output_file_formats=form.cleaned_data['output_file_formats'],
            )
            base_url = get_base_url(request)
            webhook_url = base_url + reverse('manage:rev_order_update_hook')
            webhook_url = 'http://requestb.in/sxwiousx'
            order_uri = rev.place_order(
                uri,
                output_file_formats=form.cleaned_data['output_file_formats'],
                webhook_url=webhook_url,
            )
            rev_order.uri = order_uri
            rev_order.order_number = order_uri.split('/')[-1]
            rev_order.update_status(save=False)
            rev_order.save()

            return redirect('manage:event_rev_orders', event.pk)
    else:
        url = ''
        content_type = ''
        filename = ''
        # If the event is public, and has a vidly submission, use its
        # SD version in MPEG4 format.
        if event.template.name.lower().count('vid.ly'):
            submissions = VidlySubmission.objects.filter(
                event=event,
                tag=event.template_environment['tag'],
                finished__isnull=False,
                submission_error__isnull=True,
            )
            for submission in submissions.order_by('-finished')[:1]:
                url = 'https://vid.ly/{}?content=video&format=mp4'.format(
                    submission.tag,
                )
                filename = '{}.mp4'.format(submission.tag)
                content_type = 'video/mpeg'
                # get the real URL
                response = requests.head(url)
                if response.status_code in (301, 302):
                    url = response.headers['Location']
                    filename = os.path.basename(url.split('?')[0])

        initial = {
            'url': url,
            'content_type': content_type,
            'filename': filename,
            'output_file_formats': ['Dfxp'],
        }
        form = forms.RevInputForm(initial=initial)

    context = {
        'event': event,
        'form': form,
    }
    return render(request, 'manage/new_event_rev_order.html', context)


def rev_order_update_hook(request):
    raise NotImplementedError(request.method)


@require_POST
@staff_required
@permission_required('closedcaptions.change_closedcaptions')
@transaction.atomic
def event_rev_orders_cancel(request, event_id, id):
    rev_order = get_object_or_404(RevOrder, event__id=event_id, id=id)
    rev.cancel_order(rev_order.order_number)
    rev_order.cancelled = True
    rev_order.save()
    messages.success(
        request,
        'Order cancelled',
    )
    return redirect('manage:event_rev_orders', rev_order.event.id)


@require_POST
@staff_required
@permission_required('closedcaptions.change_closedcaptions')
@transaction.atomic
def event_rev_orders_update(request, event_id, id):
    rev_order = get_object_or_404(RevOrder, event__id=event_id, id=id)
    status_before = rev_order.status
    rev_order.update_status()
    status_after = rev_order.status
    if status_before != status_after:
        messages.success(
            request,
            'Status changed from {} to {}'.format(
                status_before,
                status_after,
            )
        )
    else:
        messages.info(
            request,
            'Status unchanged',
        )
    return redirect('manage:event_rev_orders', rev_order.event.id)


@staff_required
@permission_required('closedcaptions.change_closedcaptions')
@transaction.atomic
def event_rev_orders_download(request, event_id, id, attachment_id):
    rev_order = get_object_or_404(RevOrder, event__id=event_id, id=id)
    for attachment in rev_order.get_order()['attachments']:
        if attachment['id'] == attachment_id:
            response_attachment = rev.get_attachment(attachment['id'])
            response = http.HttpResponse()
            response['Content-Type'] = (
                response_attachment.headers['Content-Type']
            )
            response['Content-Disposition'] = (
                response_attachment.headers['Content-Disposition']
            )
            response.write(response_attachment.text)
            return response
    return http.HttpResponseBadRequest(attachment_id)
