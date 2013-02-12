from django import forms
from django.template.defaultfilters import slugify
from django.conf import settings

from airmozilla.base.forms import BaseModelForm
from airmozilla.main.models import (
    SuggestedEvent,
    Event,
    Tag,
    Channel
)


class StartForm(BaseModelForm):

    class Meta:
        model = SuggestedEvent
        fields = ('title',)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(StartForm, self).__init__(*args, **kwargs)

    def clean_title(self):
        value = self.cleaned_data['title']
        if Event.objects.filter(title__iexact=value):
            raise forms.ValidationError("Event title already used")
        if SuggestedEvent.objects.filter(title__iexact=value, user=self.user):
            raise forms.ValidationError(
                "You already have a suggest event with this title"
            )
        return value


class TitleForm(BaseModelForm):

    class Meta:
        model = SuggestedEvent
        fields = ('title', 'slug')

    def clean_slug(self):
        value = self.cleaned_data['slug']
        if value:
            if Event.objects.filter(slug__iexact=value):
                raise forms.ValidationError('Already taken')
        return value

    def clean_title(self):
        value = self.cleaned_data['title']
        if Event.objects.filter(title__iexact=value):
            raise forms.ValidationError("Event title already used")
        return value

    def clean(self):
        cleaned_data = super(TitleForm, self).clean()
        if 'slug' in cleaned_data and 'title' in cleaned_data:
            if not cleaned_data['slug']:
                cleaned_data['slug'] = slugify(cleaned_data['title'])
                if Event.objects.filter(slug=cleaned_data['slug']):
                    raise forms.ValidationError('Slug already taken')
        return cleaned_data


class DescriptionForm(BaseModelForm):

    class Meta:
        model = SuggestedEvent
        fields = ('description', 'short_description')

    def __init__(self, *args, **kwargs):
        super(DescriptionForm, self).__init__(*args, **kwargs)
        self.fields['description'].help_text = (
            "Richard! Can you think of a more appropriate text here?"
        )


class DetailsForm(BaseModelForm):

    tags = forms.CharField(required=False)

    class Meta:
        model = SuggestedEvent
        fields = (
            'location',
            'start_time',
            'privacy',
            'category',
            'tags',
            'channels',
            'additional_links',
        )

    def __init__(self, *args, **kwargs):
        super(DetailsForm, self).__init__(*args, **kwargs)
        self.fields['channels'].required = False
        self.fields['location'].required = True
        self.fields['start_time'].required = True
        if 'instance' in kwargs:
            event = kwargs['instance']
            if event.pk:
                tag_format = lambda objects: ','.join(map(unicode, objects))
                tags_formatted = tag_format(event.tags.all())
                self.initial['tags'] = tags_formatted

    def clean_tags(self):
        tags = self.cleaned_data['tags']
        split_tags = [t.strip() for t in tags.split(',') if t.strip()]
        final_tags = []
        for tag_name in split_tags:
            t, __ = Tag.objects.get_or_create(name=tag_name)
            final_tags.append(t)
        return final_tags

    def clean_channels(self):
        channels = self.cleaned_data['channels']
        if not channels:
            channels.append(
                Channel.objects.get(slug=settings.DEFAULT_CHANNEL_SLUG)
            )
        return channels


class PlaceholderForm(BaseModelForm):

    class Meta:
        model = SuggestedEvent
        fields = ('placeholder_img',)


#class ParticipantsForm(BaseModelForm):
#
#    participants = forms.CharField(required=False)
#
#    class Meta:
#        model = SuggestedEvent
#        fields = ('participants',)
#
#    def clean_participants(self):
#        participants = self.cleaned_data['participants']
#        split_participants = [p.strip() for p in participants.split(',')
#                              if p.strip()]
#        final_participants = []
#        for participant_name in split_participants:
#            p = Participant.objects.get(name=participant_name)
#            final_participants.append(p)
#        return final_participants
#
