import cgi

from django.forms import widgets
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse

from airmozilla.main.models import Picture
from airmozilla.main.templatetags.jinja_helpers import thumbnail


class PictureWidget(widgets.Select):

    def __init__(self, instance, attrs=None, **kwargs):
        super(PictureWidget, self).__init__(attrs)
        self.instance = instance
        self.editable = kwargs.get('editable', True)

    def render(self, name, value, attrs=None, **__):
        if value:
            picture = Picture.objects.get(id=value)
            thumb = thumbnail(picture.file, '96x54', crop='center')
            img = (
                '<img src="%s" width="%d" height="%d" alt="%s">' % (
                    thumb.url,
                    thumb.width,
                    thumb.height,
                    picture.notes and cgi.escape(picture.notes) or ''
                )
            )
            html = (
                '<input type="hidden" name="%s" value="%d">'
                '<a href="%s" title="Current picture">%s</a> ' % (
                    name,
                    picture.id,
                    reverse('manage:picture_edit', args=(picture.id,)),
                    img,
                )
            )
            if self.editable:
                html += (
                    '<a href="%s?event=%d" '
                    'title="This will leave the editing without saving"'
                    '>Pick another</a>' % (
                        reverse('manage:picturegallery'),
                        self.instance.id
                    )
                )
            else:
                html += (
                    'You can pick a different picture later'
                )
            return mark_safe(html)
        else:
            html = (
                '<a href="%s?event=%d" '
                'title="This will leave the editing without saving">'
                'Pick a picture from the gallery</a>' % (
                    reverse('manage:picturegallery'),
                    self.instance.id,
                )
            )
            return mark_safe(html)
