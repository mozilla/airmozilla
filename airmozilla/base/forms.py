from django import forms
from django.shortcuts import render_to_response
from django.utils.safestring import mark_safe

from airmozilla.main.models import Picture
from airmozilla.main.helpers import thumbnail


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
    def render(self, name, value, attrs):
        pictures = []
        for pic in Picture.objects.all().order_by('event', '-created'):
            thumb = thumbnail(pic.file, '100x100', crop='center')
            pictures.append({
                'thumb': {
                    'url': thumb.url,
                    'width': thumb.width,
                    'height': thumb.height
                },
                'notes': pic.notes,
                'selected': value == pic.id,
                'id': pic.id})
        context = {'pictures': pictures, 'current_id': value}
        return mark_safe(render_to_response('gallery.html', context).content)

    class Media:
        css = {'all': ('css/gallery_select.css',)}
        js = ('js/gallery_select.js',)
