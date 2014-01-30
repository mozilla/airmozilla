from django import forms
from django.template.defaultfilters import slugify
from django.conf import settings
from django.template.defaultfilters import filesizeformat
from django.utils.timesince import timesince
from django.utils.safestring import mark_safe
from django.db.models import Q

from airmozilla.base.forms import BaseModelForm
from airmozilla.main.models import (
    SuggestedEvent,
    Event,
    Tag,
    Channel,
    SuggestedEventComment
)
from airmozilla.uploads.models import Upload


class StartForm(BaseModelForm):

    class Meta:
        model = SuggestedEvent
        fields = ('title', 'upcoming')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(StartForm, self).__init__(*args, **kwargs)
        self.fields['upcoming'].label = ''
        self.fields['upcoming'].widget = forms.widgets.RadioSelect(
            choices=[(True, 'Upcoming'), (False, 'Pre-recorded')]
        )

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


class ChooseFileForm(BaseModelForm):

    class Meta:
        model = SuggestedEvent
        fields = ('upload',)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(ChooseFileForm, self).__init__(*args, **kwargs)
        this_or_nothing = (
            Q(suggested_event__isnull=True) |
            Q(suggested_event=self.instance)
        )
        uploads = (
            Upload.objects
            .filter(user=self.user)
            .filter(this_or_nothing)
            .order_by('created')
        )
        self.fields['upload'].widget = forms.widgets.RadioSelect(
            choices=[(x.pk, self.describe_upload(x)) for x in uploads]
        )

    @staticmethod
    def describe_upload(upload):
        html = (
            '%s <br><span class="metadata">(%s) uploaded %s ago</span>' % (
                upload.file_name,
                filesizeformat(upload.size),
                timesince(upload.created)
            )
        )
        return mark_safe(html)


class DescriptionForm(BaseModelForm):

    class Meta:
        model = SuggestedEvent
        fields = ('description', 'short_description')

    def __init__(self, *args, **kwargs):
        super(DescriptionForm, self).__init__(*args, **kwargs)
        self.fields['description'].help_text = (
            "Write a description of your event that will entice viewers to "
            "watch.&lt;br&gt;"
            "An interesting description improves the chances of your "
            "presentation being picked up by bloggers and other websites."
            "&lt;br&gt;"
            "Please phrase your description in the present tense. "
        )
        self.fields['short_description'].help_text = (
            "This Short Description is used in public feeds and tweets.  "
            "&lt;br&gt;If your event is non-public be careful "
            "&lt;b&gt;not to "
            "disclose sensitive information here&lt;/b&gt;."
            "&lt;br&gt;If left blank the system will use the first few "
            "words of the description above."
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
            'remote_presenters',
        )

    def __init__(self, *args, **kwargs):
        super(DetailsForm, self).__init__(*args, **kwargs)
        self.fields['channels'].required = False
        if not self.instance.upcoming:
            del self.fields['location']
            del self.fields['start_time']
            del self.fields['remote_presenters']
        else:
            self.fields['location'].required = True
            self.fields['start_time'].required = True
            self.fields['location'].help_text = (
                "Choose an Air Mozilla origination point. &lt;br&gt;"
                "If the location of your event isn't on the list, "
                "choose Live Remote.  &lt;br&gt;"
                "Note that live remote dates and times are UTC."
            )
            self.fields['remote_presenters'].help_text = (
                "If there will be presenters who present remotely, please "
                "enter email addresses, names and locations about these "
                "presenters."
            )
            self.fields['remote_presenters'].widget.attrs['rows'] = 3

        if 'instance' in kwargs:
            event = kwargs['instance']
            if event.pk:
                tag_format = lambda objects: ','.join(map(unicode, objects))
                tags_formatted = tag_format(event.tags.all())
                self.initial['tags'] = tags_formatted

        self.fields['tags'].help_text = (
            "Enter some keywords to help viewers find the recording of your "
            "event. &lt;br&gt;Press return between keywords"
        )
        self.fields['channels'].help_text = (
            "Should your event appear in one or more particular "
            "Air Mozilla Channels? &lt;br&gt;If in doubt, select Main."
        )
        self.fields['additional_links'].help_text = (
            "If you have links to slides, the presenter's blog, or other "
            "relevant links, list them here and they will appear on "
            "the event page."
        )

        self.fields['additional_links'].widget.attrs['rows'] = 3

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
            return Channel.objects.filter(slug=settings.DEFAULT_CHANNEL_SLUG)
        return channels


class PlaceholderForm(BaseModelForm):

    class Meta:
        model = SuggestedEvent
        fields = ('placeholder_img',)

    def __init__(self, *args, **kwargs):
        super(PlaceholderForm, self).__init__(*args, **kwargs)
        self.fields['placeholder_img'].help_text = (
            "We need a placeholder image for your event. &lt;br&gt;"
            "A recent head-shot of the speaker is preferred. &lt;br&gt;"
            "Placeholder images should be 200 x 200 px or larger."
        )

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


class SuggestedEventCommentForm(BaseModelForm):

    class Meta:
        model = SuggestedEventComment
        fields = ('comment',)
