import collections

from django import http
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.db import transaction
from django.views.decorators.cache import cache_page
from django.db.models import Q
from django.core.urlresolvers import reverse

from jsonview.decorators import json_view

from airmozilla.manage.utils import filename_to_notes
from airmozilla.base.utils import dot_dict
from airmozilla.main.templatetags.jinja_helpers import thumbnail
from airmozilla.main.models import Event, Picture
from airmozilla.manage import forms

from .decorators import staff_required, permission_required
from .utils import can_edit_event


@staff_required
def picturegallery(request):
    context = {}
    if request.GET.get('event'):
        event = get_object_or_404(Event, id=request.GET.get('event'))
        result = can_edit_event(
            event,
            request.user,
            default='manage:picturegallery'
        )
        if isinstance(result, http.HttpResponse):
            return result

        context['event'] = event

    return render(request, 'manage/picturegallery.html', context)


@staff_required
@json_view
def picturegallery_data(request):
    context = {}
    if request.GET.get('event'):
        event = get_object_or_404(Event, id=request.GET['event'])
    else:
        event = None

    items = _get_all_pictures(event=event)

    context['pictures'] = items
    context['urls'] = {
        'manage:picture_edit': reverse('manage:picture_edit', args=('0',)),
        'manage:picture_delete': reverse('manage:picture_delete', args=('0',)),
        'manage:picture_delete_all': reverse(
            'manage:picture_delete_all', args=('0',)
        ),
        'manage:redirect_picture_thumbnail': reverse(
            'manage:redirect_picture_thumbnail', args=('0',)
        ),
        'manage:picture_event_associate': reverse(
            'manage:picture_event_associate', args=('0',)
        ),
        'manage:event_edit': reverse('manage:event_edit', args=('0',)),
    }
    context['stats'] = {
        'total_pictures': Picture.objects.all().count(),
        'event_pictures': Picture.objects.filter(event__isnull=False).count(),
    }

    return context


def _get_all_pictures(event=None):

    values = (
        'id',
        'title',
        'placeholder_img',
        'picture_id',
        # 'default_placeholder',
    )
    event_map = collections.defaultdict(list)
    cant_delete = collections.defaultdict(bool)
    for each in Event.objects.filter(picture__isnull=False).values(*values):
        event_map[each['picture_id']].append({
            'id': each['id'],
            'title': each['title']
        })
        if not each['placeholder_img']:
            # then you can definitely not delete this picture
            cant_delete[each['picture_id']] = True

    pictures = []
    values = (
        'id',
        'size',
        'width',
        'height',
        'notes',
        'created',
        'modified',
        'modified_user',
        'event_id',
        'default_placeholder',
        'is_active',
    )
    qs = Picture.objects.all()
    if event:
        qs = qs.filter(
            Q(event__isnull=True) |
            Q(event=event)
        )
        qs = qs.exclude(is_active=False)
    else:
        qs = qs.filter(event__isnull=True)
    for picture_dict in qs.order_by('event', '-created').values(*values):
        picture = dot_dict(picture_dict)
        item = {
            'id': picture.id,
            'width': picture.width,
            'height': picture.height,
            'size': picture.size,
            'created': picture.created.isoformat(),
            'events': event_map[picture.id],
            'event': picture.event_id,
            'default_placeholder': picture.default_placeholder,
            'is_active': picture.is_active,
        }
        if cant_delete.get(picture.id):
            item['cant_delete'] = True
        if picture.notes:
            item['notes'] = picture.notes
        # if picture.id in event_map:
        #     item['events'] = event_map[picture.id]
        pictures.append(item)
    return pictures


@staff_required
@permission_required('main.change_picture')
@transaction.atomic
def picture_edit(request, id):
    picture = get_object_or_404(Picture, id=id)
    context = {'picture': picture}

    if request.method == 'POST':
        form = forms.PictureForm(request.POST, request.FILES, instance=picture)
        if form.is_valid():
            picture = form.save()
            if picture.default_placeholder:
                # make all others NOT-default
                qs = (
                    Picture.objects
                    .exclude(id=picture.id)
                    .filter(default_placeholder=True)
                )
                for other in qs:
                    other.default_placeholder = False
                    other.save()
            return redirect('manage:picturegallery')
    else:
        form = forms.PictureForm(instance=picture)
    context['form'] = form
    return render(request, 'manage/picture_edit.html', context)


@staff_required
@permission_required('main.delete_picture')
@transaction.atomic
@json_view
def picture_delete(request, id):
    picture = get_object_or_404(Picture, id=id)
    for event in Event.objects.filter(picture=picture):
        if not event.placeholder_img:
            return http.HttpResponseBadRequest("Can't delete this")
    picture.delete()
    return True


@require_POST
@staff_required
@permission_required('main.delete_picture')
@transaction.atomic
@json_view
def picture_delete_all(request, id):
    event = get_object_or_404(Event, id=id)
    pictures = Picture.objects.filter(event=event)
    if event.picture and event.picture in pictures:
        assert event.placeholder_img
        event.picture = None
        event.save()
    pictures.delete()
    return True


@staff_required
@permission_required('main.add_picture')
@transaction.atomic
@json_view
def picture_add(request):
    context = {}
    if request.GET.get('event'):
        event = get_object_or_404(Event, id=request.GET.get('event'))
        result = can_edit_event(
            event,
            request.user,
            default='manage:picturegallery'
        )
        if isinstance(result, http.HttpResponse):
            return result

        context['event'] = event
    if request.method == 'POST':
        if request.POST.get('remove'):
            # this is for when you change your mind
            size = request.POST['size']
            filename = request.POST['name']
            notes = filename_to_notes(filename)
            matches = Picture.objects.filter(
                notes=notes,
                size=int(size),
                modified_user=request.user
            )
            for picture in matches.order_by('-created')[:1]:
                picture.delete()
                return True
            return False

        form = forms.PictureForm(request.POST, request.FILES)
        if form.is_valid():
            picture = form.save(commit=False)
            picture.modified_user = request.user
            picture.is_active = True
            picture.save()
            return redirect('manage:picturegallery')
    else:
        form = forms.PictureForm()
    context['form'] = form
    return render(request, 'manage/picture_add.html', context)


@cache_page(60)
def redirect_picture_thumbnail(request, id):
    picture = get_object_or_404(Picture, id=id)
    geometry = request.GET.get('geometry', '100x100')
    crop = request.GET.get('crop', 'center')
    thumb = thumbnail(picture.file, geometry, crop=crop)
    return redirect(thumb.url)


@staff_required
@require_POST
@transaction.atomic
@permission_required('main.change_event')
@json_view
def picture_event_associate(request, id):
    picture = get_object_or_404(Picture, id=id)
    if not request.POST.get('event'):
        return http.HttpResponseBadRequest("Missing 'event'")
    event = get_object_or_404(Event, id=request.POST['event'])
    event.picture = picture
    event.save()
    return True
