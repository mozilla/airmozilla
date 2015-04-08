from django import forms

from airmozilla.base.forms import BaseModelForm, BaseForm
from airmozilla.main.models import Event


class StartForm(BaseForm):

    name = forms.CharField(
        label='Title',
    )

    # def clean_name(self):
    #     value = self.cleaned_data['name'].strip()
    #     if ' ' in value:
    #         raise forms.ValidationError('Can not contain a space')
    #     if not fetch_user(value, is_username='@' not in value):
    #         if '@' in value:
    #             raise forms.ValidationError(
    #                 'No Mozillians account by that email'
    #             )
    #         else:
    #             raise forms.ValidationError(
    #                 'No Mozillians account by that username'
    #             )
    #     return value


class DetailsForm(BaseModelForm):

    class Meta:
        model = Event
        fields = (
            'privacy',
            'description',
            'additional_links',
        )

    def __init__(self, *args, **kwargs):
        super(DetailsForm, self).__init__(*args, **kwargs)

        self.fields['privacy'].choices = [
            (Event.PRIVACY_PUBLIC, 'Public so friends and family can view'),
            (Event.PRIVACY_CONTRIBUTORS, 'Private (only Mozillians can view)'),
            (Event.PRIVACY_COMPANY, 'Private (only Mozilla staff can view)'),
        ]
        self.fields['additional_links'].label = 'Links'

        self.fields['additional_links'].help_text = (
            "If you have links to slides, the presenter's blog, or other "
            "relevant links, list them here and they will appear on "
            "the event page."
        )

        self.fields['additional_links'].widget.attrs['rows'] = 3


class PlaceholderForm(BaseModelForm):

    class Meta:
        model = Event
        fields = ('placeholder_img',)

    def __init__(self, *args, **kwargs):
        super(PlaceholderForm, self).__init__(*args, **kwargs)
        self.fields['placeholder_img'].label = 'File upload'
        self.fields['placeholder_img'].help_text = (
            "Please make it a recent picture of you.&lt;br&gt;"
            "Placeholder images should be 200 x 200 px or larger."
        )
