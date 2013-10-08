from django import forms
from airmozilla.base.forms import BaseForm


class CalendarDataForm(BaseForm):

    start = forms.IntegerField()
    end = forms.IntegerField()

    def clean(self):
        cleaned_data = super(CalendarDataForm, self).clean()
        if 'end' in cleaned_data and 'start' in cleaned_data:
            if cleaned_data['end'] <= cleaned_data['start']:
                raise forms.ValidationError('end <= start')
        return cleaned_data
