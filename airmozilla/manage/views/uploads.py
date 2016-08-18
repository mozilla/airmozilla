from django import http
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.urlresolvers import reverse

from airmozilla.base.utils import paginate, delete_s3_keys_by_urls
from airmozilla.main.models import Event
from airmozilla.uploads.models import Upload

from .decorators import superuser_required


@superuser_required
def uploads(request):
    event = None

    if request.method == 'POST':
        event = get_object_or_404(Event, id=request.POST['event'])
        ids = request.POST.getlist('ids')
        deletions = 0
        # first check all before attempting to delete
        uploads = Upload.objects.filter(event=event, id__in=ids)
        for upload in uploads:
            if upload.get_vidly_submissions().exists():
                return http.HttpResponseBadRequest(
                    'Upload used by a Vid.ly submission'
                )
        for upload in uploads:
            if delete_s3_keys_by_urls(upload.url):
                deletions += 1
                upload.delete()
        messages.success(
            request,
            '{} upload(s) deleted'.format(deletions)
        )
        url = reverse('manage:uploads') + '?event={}'.format(event.id)
        return redirect(url)

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
