from django import forms
from django.shortcuts import render_to_response
from django.utils.safestring import mark_safe
from django.db.models import Q

from airmozilla.main.models import Picture
from airmozilla.main.templatetags.jinja_helpers import thumbnail


class _BaseForm(object):
    def clean(self):
        cleaned_data = super(_BaseForm, self).clean()
        for field in cleaned_data:
            if isinstance(cleaned_data[field], basestring):
                cleaned_data[field] = (
                    cleaned_data[field].replace('\r\n', '\n')
                    .replace(u'\u2018', "'").replace(u'\u2019', "'").strip())

        return cleaned_data


class BaseModelForm(_BaseForm, forms.ModelForm):
    pass


class BaseForm(_BaseForm, forms.Form):
    pass


class GallerySelect(forms.widgets.Widget):
    """ Produces a gallery of all Pictures for the user to select from. """

    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        super(GallerySelect, self).__init__(*args, **kwargs)

    def render(self, name, value, attrs):
        pictures = []
        qs = Picture.objects.all()
        if self.event:
            qs = qs.filter(
                Q(event__isnull=True) |
                Q(event=self.event)
            )
            # If the current event does use an inactive picture,
            # let it still be a choice.
            if self.event.picture_id:
                qs = qs.filter(
                    Q(is_active=True) | Q(id=self.event.picture_id)
                )
            else:
                qs = qs.filter(is_active=True)
        else:
            qs = qs.filter(
                event__isnull=True,
                is_active=True,
            )
        for pic in qs.order_by('event', '-created'):
            thumb = thumbnail(pic.file, '160x90', crop='center')
            pictures.append({
                'thumb': {
                    'url': thumb.url,
                    'width': thumb.width,
                    'height': thumb.height
                },
                'notes': pic.notes,
                'selected': value == pic.id,
                'id': pic.id,
            })
        context = {
            'pictures': pictures,
            'current_id': value,
            'name': name
        }
        return mark_safe(render_to_response('gallery.html', context).content)

    class Media:
        # NOTE! At the moment, these are replicated manually wherever
        # this form widget is used. That's because jinja offline compression
        # with {{ form.media.js }} doesn't work.
        css = {'all': ('css/gallery_select.css',)}
        js = ('js/gallery_select.js',)
