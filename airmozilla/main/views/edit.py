import json

from django import http
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction

from jsonview.decorators import json_view
from sorl.thumbnail import get_thumbnail

from airmozilla.main import forms
from airmozilla.main.models import (
    EventRevision,
    Tag,
    Channel,
)
from airmozilla.main.views.pages import EventView


class EventEditView(EventView):
    template_name = 'main/event_edit.html'

    def can_edit_event(self, event, request):
        # this might change in the future to only be
        # employees and vouched mozillians
        return request.user.is_active

    def cant_edit_event(self, event, user):
        return redirect('main:event', event.slug)

    @staticmethod
    def event_to_dict(event):
        picture_id = event.picture.id if event.picture else None
        data = {
            'event_id': event.id,
            'title': event.title,
            'description': event.description,
            'short_description': event.short_description,
            'channels': [x.pk for x in event.channels.all()],
            'tags': ', '.join([x.name for x in event.tags.all()]),
            'call_info': event.call_info,
            'additional_links': event.additional_links,
            'recruitmentmessage': None,
            'picture': picture_id
        }
        if event.recruitmentmessage_id:
            data['recruitmentmessage'] = event.recruitmentmessage_id
        if event.placeholder_img:
            data['placeholder_img'] = event.placeholder_img.url
            if event.picture:
                file = event.picture.file
            else:
                file = event.placeholder_img
            data['thumbnail_url'] = (
                get_thumbnail(
                    file,
                    '121x68',
                    crop='center'
                ).url
            )
        return data

    def get(self, request, slug, form=None, conflict_errors=None):
        event = self.get_event(slug, request)
        if isinstance(event, http.HttpResponse):
            return event

        if not self.can_view_event(event, request):
            return self.cant_view_event(event, request)
        if not self.can_edit_event(event, request):
            return self.cant_edit_event(event, request)

        initial = self.event_to_dict(event)
        if form is None:
            form = forms.EventEditForm(initial=initial, event=event)
            if not request.user.has_perm('main.change_recruitmentmessage'):
                del form.fields['recruitmentmessage']

        context = {
            'event': event,
            'form': form,
            'previous': json.dumps(initial),
            'conflict_errors': conflict_errors,
        }
        if 'thumbnail_url' in initial:
            context['thumbnail_url'] = initial['thumbnail_url']

        context['revisions'] = (
            EventRevision.objects
            .filter(event=event)
            .order_by('-created')
            .select_related('user')
        )

        return render(request, self.template_name, context)

    @transaction.atomic
    @json_view
    def post(self, request, slug):
        event = self.get_event(slug, request)
        if isinstance(event, http.HttpResponse):
            return event

        if not self.can_view_event(event, request):
            return self.cant_view_event(event, request)
        if not self.can_edit_event(event, request):
            return self.cant_edit_event(event, request)

        previous = request.POST['previous']
        previous = json.loads(previous)
        form = forms.EventEditForm(request.POST, request.FILES, event=event)
        base_revision = None

        if form.is_valid():
            if not EventRevision.objects.filter(event=event).count():
                base_revision = EventRevision.objects.create_from_event(event)

            cleaned_data = form.cleaned_data
            if 'placeholder_img' in request.FILES:
                cleaned_data['picture'] = None

            changes = {}
            conflict_errors = []
            for key, value in cleaned_data.items():

                # figure out what the active current value is in the database
                if key == 'placeholder_img':
                    if (
                        event.picture and
                        'placeholder_img' not in request.FILES
                    ):
                        current_value = event.picture.file.url
                    else:
                        if event.placeholder_img:
                            current_value = event.placeholder_img.url
                        else:
                            current_value = None

                elif key == 'tags':
                    current_value = ', '.join(x.name for x in event.tags.all())
                elif key == 'channels':
                    current_value = [x.pk for x in event.channels.all()]
                elif key == 'picture':
                    current_value = event.picture.id if event.picture else None
                elif key == 'event_id':
                    pass
                else:
                    current_value = getattr(event, key)
                    if key == 'recruitmentmessage':
                        if current_value:
                            current_value = current_value.pk

                if key == 'channels':
                    prev = set([
                        Channel.objects.get(pk=x)
                        for x in previous[key]
                    ])
                    value = set(value)
                    for channel in prev - value:
                        event.channels.remove(channel)
                    for channel in value - prev:
                        event.channels.add(channel)
                    if prev != value:
                        changes['channels'] = {
                            'from': ', '.join(
                                sorted(x.name for x in prev)
                            ),
                            'to': ', '.join(
                                sorted(x.name for x in value)
                            )
                        }
                elif key == 'tags':
                    value = set([
                        x.strip()
                        for x in value.split(',')
                        if x.strip()
                    ])
                    prev = set([
                        x.strip()
                        for x in previous['tags'].split(',')
                        if x.strip()
                    ])
                    for tag in prev - value:
                        tag_obj = Tag.objects.get(name=tag)
                        event.tags.remove(tag_obj)
                    for tag in value - prev:
                        try:
                            tag_obj = Tag.objects.get(name__iexact=tag)
                        except Tag.DoesNotExist:
                            tag_obj = Tag.objects.create(name=tag)
                        except Tag.MultipleObjectsReturned:
                            tag_obj, = Tag.objects.filter(name__iexact=tag)[:1]
                        event.tags.add(tag_obj)
                    if prev != value:
                        changes['tags'] = {
                            'from': ', '.join(sorted(prev)),
                            'to': ', '.join(sorted(value))
                        }
                elif key == 'placeholder_img':
                    if value:
                        changes[key] = {
                            'from': (
                                event.placeholder_img and
                                event.placeholder_img.url or
                                ''
                            ),
                            'to': '__saved__event_placeholder_img'
                        }
                        event.placeholder_img = value
                elif key == 'recruitmentmessage':
                    prev = event.recruitmentmessage
                    event.recruitmentmessage = value
                    if value != prev:
                        changes[key] = {
                            'from': prev,
                            'to': event.recruitmentmessage
                        }
                elif key == 'event_id':
                    pass
                else:
                    if value != previous[key]:
                        changes[key] = {
                            'from': previous[key],
                            'to': value
                        }
                        setattr(event, key, value)
                if key in changes:
                    # you wanted to change it, but has your reference changed
                    # since you loaded it?
                    previous_value = previous.get(key)
                    if previous_value != current_value:
                        conflict_errors.append(key)
                        continue

            if conflict_errors:
                return self.get(
                    request,
                    slug,
                    form=form,
                    conflict_errors=conflict_errors
                )
            elif changes:
                event.save()
                EventRevision.objects.create_from_event(
                    event,
                    user=request.user,
                )
            else:
                if base_revision:
                    base_revision.delete()

            return redirect('main:event', event.slug)

        return self.get(request, slug, form=form)


class EventRevisionView(EventView):

    template_name = 'main/revision_change.html'
    difference = False

    def can_view_event(self, event, request):
        return (
            request.user.is_active and
            super(EventRevisionView, self).can_view_event(event, request)
        )

    def get(self, request, slug, id):
        event = self.get_event(slug, request)
        if isinstance(event, http.HttpResponse):
            return event

        if not self.can_view_event(event, request):
            return self.cant_view_event(event, request)

        revision = get_object_or_404(
            EventRevision,
            event=event,
            pk=id
        )

        if self.difference:
            # compare this revision against the current event
            previous = event
        else:
            previous = revision.get_previous_by_created(event=event)

        fields = (
            ('title', 'Title'),
            ('placeholder_img', 'Placeholder image'),
            ('picture', 'Picture'),
            ('description', 'Description'),
            ('short_description', 'Short description'),
            ('channels', 'Channels'),
            ('tags', 'Tags'),
            ('call_info', 'Call info'),
            ('additional_links', 'Additional links'),
            ('recruitmentmessage', 'Recruitment message'),
        )
        differences = []

        def getter(key, obj):
            if key == 'tags' or key == 'channels':
                return ', '.join(sorted(
                    x.name for x in getattr(obj, key).all()
                ))
            return getattr(obj, key)

        class _Difference(object):
            """use a simple class so we can use dot notation in templates"""
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        for key, label in fields:
            before = getter(key, previous)
            after = getter(key, revision)
            if before != after:
                differences.append(_Difference(
                    key=key,
                    label=label,
                    before=before,
                    after=after
                ))

        context = {}
        context['difference'] = self.difference
        context['event'] = event
        context['revision'] = revision
        context['differences'] = differences
        return render(request, self.template_name, context)
