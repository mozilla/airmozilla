import re

from django import forms
from django.db.models import Q
from django.contrib.auth.models import User

from airmozilla.base.forms import BaseModelForm, BaseForm, GallerySelect
from airmozilla.main.models import (
    EventRevision,
    RecruitmentMessage,
    Event,
    Channel,
    Chapter,
    Tag,
)
from airmozilla.comments.models import Discussion


class CalendarDataForm(BaseForm):

    start = forms.DateTimeField()
    end = forms.DateTimeField()

    def clean(self):
        cleaned_data = super(CalendarDataForm, self).clean()
        if 'end' in cleaned_data and 'start' in cleaned_data:
            if cleaned_data['end'] <= cleaned_data['start']:
                raise forms.ValidationError('end <= start')
        return cleaned_data


class PinForm(BaseForm):
    pin = forms.CharField(max_length=20)

    def __init__(self, *args, **kwargs):
        if 'instance' in kwargs:
            self.instance = kwargs.pop('instance')
            assert self.instance.pin, "event doesn't have a pin"
        else:
            self.instance = None
        super(PinForm, self).__init__(*args, **kwargs)

    def clean_pin(self):
        value = self.cleaned_data['pin'].strip()
        if value != self.instance.pin:
            raise forms.ValidationError("Incorrect pin")
        return value


class TagsModelMultipleChoiceField(forms.ModelMultipleChoiceField):

    def clean(self, value):
        if not value:
            return self.queryset.none()
        # convert the values to IDs
        pks = []
        for pk in value:
            if not pk:
                continue
            if not pk.isdigit():
                for tag in Tag.objects.filter(name__iexact=pk):
                    pks.append(tag.id)
                    break
                else:
                    pks.append(Tag.objects.create(name=pk).id)
            else:
                pks.append(int(pk))
        return super(TagsModelMultipleChoiceField, self).clean(pks)


class EventEditForm(BaseModelForm):

    event_id = forms.CharField(widget=forms.HiddenInput())
    tags = TagsModelMultipleChoiceField(
        Tag.objects.all(),
        required=False,
    )

    class Meta:
        model = EventRevision
        exclude = ('event', 'user', 'created', 'change')

    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event', None)
        no_tag_choices = kwargs.pop('no_tag_choices', None)
        super(EventEditForm, self).__init__(*args, **kwargs)

        if no_tag_choices:
            self.fields['tags'].queryset = self.event.tags.all()
        self.fields['tags'].help_text = ''
        self.fields['channels'].queryset = (
            Channel.objects
            .filter(Q(never_show=False) | Q(id__in=self.event.channels.all()))
        )

        self.fields['placeholder_img'].required = False
        self.fields['placeholder_img'].label = (
            'Upload a picture from your computer'
        )
        self.fields['channels'].help_text = ''
        self.fields['recruitmentmessage'].label = 'Recruitment message'
        self.fields['recruitmentmessage'].required = False
        self.fields['recruitmentmessage'].queryset = (
            RecruitmentMessage.objects.filter(active=True)
        )
        self.fields['picture'].widget = GallerySelect(event=self.event)
        self.fields['picture'].label = (
            'Select an existing picture from the gallery'
        )
        if not (self.event.is_upcoming() or self.event.is_live()):
            del self.fields['call_info']

    def clean(self):
        cleaned_data = super(EventEditForm, self).clean()
        event = Event.objects.get(id=cleaned_data.get('event_id'))
        placeholder_img = cleaned_data.get(
            'placeholder_img') or event.placeholder_img
        picture = cleaned_data.get('picture') or event.picture
        if not placeholder_img and not picture:
            raise forms.ValidationError('Events needs to have a picture')
        return cleaned_data


class EventDiscussionForm(BaseModelForm):

    moderators = forms.CharField(
        widget=forms.widgets.Textarea()
    )

    class Meta:
        model = Discussion
        exclude = ('event', )

    def __init__(self, *args, **kwargs):
        self.event = kwargs.pop('event')
        super(EventDiscussionForm, self).__init__(*args, **kwargs)

        self.fields['moderators'].widget = forms.widgets.Textarea()
        self.fields['moderators'].help_text = (
            "One email address per line or separated by commas."
        )

    def clean_moderators(self):
        value = self.cleaned_data['moderators']
        emails = [x for x in re.split('[,\s]', value) if x.strip()]
        users = []
        for email in emails:
            try:
                users.append(User.objects.get(email__iexact=email))
            except User.DoesNotExist:
                raise forms.ValidationError(
                    "{0} does not exist as a Air Mozilla user".format(
                        email
                    )
                )
        if not users:
            raise forms.ValidationError(
                "You must have at least one moderator"
            )
        return users


class ExecutiveSummaryForm(BaseForm):

    start = forms.DateTimeField(required=False)

    def clean_start(self):
        value = self.cleaned_data['start']
        if value and value.weekday() != 0:
            raise forms.ValidationError("Not a Monday")
        return value


class ThumbnailsForm(BaseForm):
    id = forms.IntegerField()
    width = forms.IntegerField()
    height = forms.IntegerField()


class EventEditTagsForm(BaseModelForm):

    event_id = forms.CharField(widget=forms.HiddenInput())
    tags = forms.CharField(required=False)

    class Meta:
        model = Event
        fields = ['tags', 'event_id']


class EventChapterEditForm(BaseModelForm):

    class Meta:
        model = Chapter
        fields = ('timestamp', 'text')

    def __init__(self, event, *args, **kwargs):
        self.event = event
        super(EventChapterEditForm, self).__init__(*args, **kwargs)

    def clean_timestamp(self):
        timestamp = self.cleaned_data['timestamp']
        if timestamp > self.event.duration:
            raise forms.ValidationError(
                'Timestamp longer than the video itself'
            )
        return timestamp
