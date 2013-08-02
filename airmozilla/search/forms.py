from django import forms

from airmozilla.base.forms import BaseForm


class SearchForm(BaseForm):

    q = forms.CharField(required=True)

    def clean_q(self):
        value = self.cleaned_data['q']
        if len(value) <= 2:
            raise forms.ValidationError('Too short')

        return value
