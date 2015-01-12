import collections

from django import http
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction

from jsonview.decorators import json_view

from airmozilla.main.models import (
    Event,
    Location,
    SuggestedEvent,
    LocationDefaultEnvironment
)
from airmozilla.manage import forms

from .decorators import (
    staff_required,
    permission_required,
    cancel_redirect
)


@staff_required
@permission_required('main.change_location')
def locations(request):
    context = {}
    locations = Location.objects.all()
    context['locations'] = locations

    associated_events = collections.defaultdict(int)
    associated_suggested_events = collections.defaultdict(int)

    events = Event.objects.exclude(location__isnull=True)
    for each in events.values('location_id'):
        associated_events[each['location_id']] += 1

    suggested_events = SuggestedEvent.objects.exclude(location__isnull=True)
    for each in suggested_events.values('location_id'):
        associated_suggested_events[each['location_id']] += 1

    context['associated_events'] = associated_events
    context['associated_suggested_events'] = associated_suggested_events

    return render(request, 'manage/locations.html', context)


@staff_required
@permission_required('main.change_location')
@cancel_redirect('manage:locations')
@transaction.commit_on_success
def location_edit(request, id):
    location = get_object_or_404(Location, id=id)

    if request.method == 'POST' and request.POST.get('delete'):
        LocationDefaultEnvironment.objects.get(
            id=request.POST.get('delete'),
            location=location
        ).delete()
        messages.info(request, 'Configuration deleted.')
        return redirect('manage:location_edit', location.id)

    if request.method == 'POST' and not request.POST.get('default'):
        form = forms.LocationEditForm(request.POST, instance=location)
        if form.is_valid():
            form.save()
            messages.info(request, 'Location "%s" saved.' % location)
            return redirect('manage:locations')
    else:
        form = forms.LocationEditForm(instance=location)

    if request.method == 'POST' and request.POST.get('default'):

        default_environment_form = forms.LocationDefaultEnvironmentForm(
            request.POST
        )
        if default_environment_form.is_valid():
            fc = default_environment_form.cleaned_data

            if LocationDefaultEnvironment.objects.filter(
                location=location,
                privacy=fc['privacy']
            ):
                # there can only be one of them
                lde = LocationDefaultEnvironment.objects.get(
                    location=location,
                    privacy=fc['privacy']
                )
                lde.template = fc['template']
            else:
                lde = LocationDefaultEnvironment.objects.create(
                    location=location,
                    privacy=fc['privacy'],
                    template=fc['template']
                )
            lde.template_environment = fc['template_environment']
            lde.save()
            messages.info(request, 'Default location environment saved.')
            return redirect('manage:location_edit', location.id)
    else:
        default_environment_form = forms.LocationDefaultEnvironmentForm()

    context = {
        'form': form,
        'location': location,
        'default_environment_form': default_environment_form
    }

    context['location_default_environments'] = (
        LocationDefaultEnvironment.objects
        .filter(location=location).order_by('privacy', 'template')
    )

    return render(request, 'manage/location_edit.html', context)


@staff_required
@permission_required('main.add_location')
@cancel_redirect('manage:events')
@transaction.commit_on_success
def location_new(request):
    if request.method == 'POST':
        form = forms.LocationEditForm(request.POST, instance=Location())
        if form.is_valid():
            form.save()
            messages.success(request, 'Location created.')
            return redirect('manage:locations')
    else:
        form = forms.LocationEditForm()
    return render(request, 'manage/location_new.html', {'form': form})


@staff_required
@permission_required('main.delete_location')
@transaction.commit_on_success
def location_remove(request, id):
    location = get_object_or_404(Location, id=id)
    if request.method == 'POST':
        # This is only allowed if there are no events or suggested events
        # associated with this location
        if (
            Event.objects.filter(location=location) or
            SuggestedEvent.objects.filter(location=location)
        ):
            return http.HttpResponseBadRequest("Still being used")

        location.delete()
        messages.info(request, 'Location "%s" removed.' % location.name)
    return redirect('manage:locations')


@staff_required
@json_view
def location_timezone(request):
    """Responds with the timezone for the requested Location.  Used to
       auto-fill the timezone form in event requests/edits."""
    if not request.GET.get('location'):
        raise http.Http404('no location')
    location = get_object_or_404(Location, id=request.GET['location'])
    return {'timezone': location.timezone}
