from django import forms
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from airmozilla.base.forms import BaseModelForm
from airmozilla.main.models import Event, Tag, Channel
from airmozilla.uploads.models import Upload


class SaveForm(BaseModelForm):

    class Meta:
        model = Upload
        fields = ('url', 'file_name', 'mime_type', 'size', 'upload_time')


class ChannelsFieldRenderer(forms.widgets.CheckboxFieldRenderer):

    def __init__(self, *args, **kwargs):
        self.popular = kwargs.pop('popular', [])
        super(ChannelsFieldRenderer, self).__init__(*args, **kwargs)

    def render(self):
        context = {
            'choices': [
                dict(id=x[0], name=x[1]) for x in self.choices if not x[-1]
            ],
            'popular': [
                dict(id=x[0], name=x[1]) for x in self.choices if x[-1]
            ],
            'name': self.name,
            'attrs': self.attrs,
        }

        html = render_to_string('new/channels_field.html', context)
        return mark_safe(html)


class ChannelsSelectWidget(forms.widgets.CheckboxSelectMultiple):
    renderer = ChannelsFieldRenderer

    def __init__(self, *args, **kwargs):
        choices = []
        for id, name in kwargs.pop('popular', []):
            choices.append((id, name, True))
        for id, name in kwargs.get('choices', []):
            choices.append((id, name, False))
        super(ChannelsSelectWidget, self).__init__(*args, **kwargs)
        self.choices = choices


class ChannelsModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    widget = ChannelsSelectWidget
    help_text = ''


class DetailsForm(BaseModelForm):

    tags = forms.CharField(
        label='Tags (comma separated, optional)',
        required=False,
        widget=forms.widgets.Textarea(attrs={
            'rows': 1
        })
    )
    channels = ChannelsModelMultipleChoiceField(
        Channel.objects.exclude(never_show=True),
        label='Channels',
        required=False,
    )

    class Meta:
        model = Event
        fields = (
            'title',
            'privacy',
            'description',
            'additional_links',
            'tags',
            'channels',
        )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(DetailsForm, self).__init__(*args, **kwargs)

        # make it into a list because we might append to it later
        popular = list(Channel.objects.filter(always_show=True))
        popular_ids = [x.id for x in popular]
        # include the channel you used last time too
        if user:
            user_past_events = Event.objects.filter(creator=self.user)
            for event in user_past_events.order_by('-created')[:1]:
                for channel in event.channels.all():
                    if channel.id not in popular_ids:
                        popular.append(channel)
                        popular_ids.append(channel.id)
        self.fields['channels'].widget = ChannelsSelectWidget(
            popular=[
                (x.id, x.name) for x in popular
            ],
            choices=[
                (x[0], x[1]) for x in self.fields['channels'].choices
                if x[0] not in popular_ids
            ]
        )

        self.fields['privacy'].choices = [
            (Event.PRIVACY_PUBLIC, 'Public'),
            (
                Event.PRIVACY_CONTRIBUTORS,
                'Contributors (only vouched Mozillians)'
            ),
            (Event.PRIVACY_COMPANY, 'Staff (MoCo/MoFo only)'),
        ]
        self.fields['additional_links'].label = 'Links (optional)'

        self.fields['additional_links'].widget.attrs['title'] = (
            "If you have links to slides, the presenter's blog, or other "
            "relevant links, list them here and they will appear on "
            "the event page."
        )

        self.fields['description'].widget.attrs['rows'] = 3
        self.fields['additional_links'].widget.attrs['rows'] = 2
        for field in self.fields:
            self.fields[field].widget.attrs['ng-model'] = (
                'event.{0}'.format(field)
            )
            self.fields[field].widget.attrs['ng-class'] = (
                "{'has-error': errors.%s}" % (field,)
            )

    def clean_tags(self):
        tags = self.cleaned_data['tags']
        split_tags = [t.strip() for t in tags.split(',') if t.strip()]
        final_tags = []
        for tag_name in split_tags:
            t, __ = Tag.objects.get_or_create(name=tag_name)
            final_tags.append(t)
        return final_tags


class PictureForm(BaseModelForm):

    class Meta:
        model = Event
        fields = ('picture',)

    def __init__(self, *args, **kwargs):
        super(PictureForm, self).__init__(*args, **kwargs)
        self.fields['picture'].required = True

    def clean_picture(self):
        value = self.cleaned_data['picture']
        if value.event != self.instance:
            raise forms.ValidationError(
                'Picture not a choice for this event'
            )
        return value
