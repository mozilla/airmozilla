import datetime

from django import forms

from airmozilla.base.forms import BaseModelForm, BaseForm, GallerySelect
from airmozilla.main.models import EventRevision, RecruitmentMessage, Event


class CalendarDataForm(BaseForm):

    start = forms.IntegerField()
    end = forms.IntegerField()

    def clean_start(self):
        try:
            return datetime.datetime.fromtimestamp(
                self.cleaned_data['start']
            )
        except ValueError as x:
            raise forms.ValidationError(x)

    def clean_end(self):
        try:
            return datetime.datetime.fromtimestamp(
                self.cleaned_data['end']
            )
        except ValueError as x:
            raise forms.ValidationError(x)

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


class EventEditForm(BaseModelForm):

    event_id = forms.CharField(widget=forms.HiddenInput())
    tags = forms.CharField(required=False)

    class Meta:
        model = EventRevision
        exclude = ('event', 'user', 'created', 'change')

    def __init__(self, *args, **kwargs):
        super(EventEditForm, self).__init__(*args, **kwargs)
        self.fields['placeholder_img'].required = False
        self.fields['placeholder_img'].label = (
            'Upload a picture from your computer')
        self.fields['channels'].help_text = ""
        self.fields['recruitmentmessage'].label = 'Recruitment message'
        self.fields['recruitmentmessage'].required = False
        self.fields['recruitmentmessage'].queryset = (
            RecruitmentMessage.objects.filter(active=True)
        )
        self.fields['picture'].widget = GallerySelect()
        self.fields['picture'].label = (
            'Select an existing picture from the gallery'
        )

    def clean(self):
        cleaned_data = super(EventEditForm, self).clean()
        event = Event.objects.get(id=cleaned_data.get('event_id'))
        placeholder_img = cleaned_data.get(
            'placeholder_img') or event.placeholder_img
        picture = cleaned_data.get('picture') or event.picture
        if not placeholder_img and not picture:
            raise forms.ValidationError('Events needs to have a picture')
        return cleaned_data
