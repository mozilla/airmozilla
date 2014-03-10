import datetime

from django import forms
from airmozilla.base.forms import BaseForm


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
