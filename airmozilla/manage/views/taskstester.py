import time

from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.urlresolvers import reverse

from airmozilla.main.models import Event
from airmozilla.manage.tasks import sample_updater
from .decorators import superuser_required


@superuser_required
def tasks_tester(request):
    context = {}
    if request.method == 'POST':
        event, = Event.objects.all().order_by('-modified')[:1]
        original_event_modified = event.modified
        assert sample_updater.delay(event.id)
        seconds = 0
        for i in range(5):
            event, = Event.objects.all().order_by('-modified')[:1]
            if event.modified > original_event_modified:
                messages.success(
                    request,
                    'Waited %d seconds :)' % (seconds,)
                )
                break
            seconds += i
            time.sleep(i)
        else:
            messages.error(
                request,
                'Waited %d seconds :(' % seconds
            )
        return redirect(reverse('manage:tasks_tester'))
    return render(request, 'manage/tasks_tester.html', context)
