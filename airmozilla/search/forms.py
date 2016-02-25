from django import forms
from django.db.models import QuerySet

from airmozilla.base.forms import BaseForm
from airmozilla.main.models import Event, Channel, Tag


class SearchForm(BaseForm):

    q = forms.CharField(required=True)

    def clean_q(self):
        value = self.cleaned_data['q']
        if len(value) <= 2:
            raise forms.ValidationError('Too short')

        return value


class SavedSearchForm(BaseForm):

    title_include = forms.CharField(required=False, label='Title (must)')
    title_exclude = forms.CharField(required=False, label='Title (exclude)')

    tags_include = forms.ModelMultipleChoiceField(
        Tag.objects.all().order_by('name'),
        required=False,
        label='Tags (must)',
    )
    tags_exclude = forms.ModelMultipleChoiceField(
        Tag.objects.all().order_by('name'),
        required=False,
        label='Tags (exclude)'
    )

    channels_include = forms.ModelMultipleChoiceField(
        Channel.objects.exclude(never_show=True),
        required=False,
        label='Channels (must)'
    )
    channels_exclude = forms.ModelMultipleChoiceField(
        Channel.objects.exclude(never_show=True),
        required=False,
        label='Channels (exclude)'
    )

    privacy = forms.MultipleChoiceField(
        choices=Event.PRIVACY_CHOICES,
        required=False,
        label='Privacy (optional)',
        widget=forms.widgets.CheckboxSelectMultiple(),
    )

    name = forms.CharField(required=False, label='Name this search (optional)')

    def __init__(self, *args, **kwargs):
        super(SavedSearchForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].required = False
            if isinstance(self.fields[field], forms.ModelMultipleChoiceField):
                self.fields[field].help_text = ''

    @classmethod
    def convert_filters(cls, filters, pks=False):
        """return a dict of the filters converted to real objects (or just
        their primary keys)
        """
        data = {}
        for key, values in filters.items():
            if key == 'privacy':
                data[key] = values
                continue
            for instruction in values:
                combined = '{}_{}'.format(key, instruction)
                if values.get(instruction):
                    value = values[instruction]
                    # if it's a list of IDs (digits), it can be converted
                    # to a query set
                    if key == 'tags':
                        value = Tag.objects.filter(id__in=value)
                    elif key == 'channels':
                        value = Channel.objects.filter(id__in=value)

                    # This is useful when feeding this resulting dict
                    # to render a form.
                    if isinstance(value, QuerySet):
                        value = [x.pk for x in value]

                    data[combined] = value

        return data

    def clean_privacy(self):
        # If someone selects all of them, select none
        value = self.cleaned_data['privacy']
        if value and len(value) == len(Event.PRIVACY_CHOICES):
            value = []
        return value

    def clean(self):
        cleaned_data = super(SavedSearchForm, self).clean()
        # check that no freetext word is used in both places
        title_include = set(
            x.lower() for x in cleaned_data['title_include'].split()
            if x.strip()
        )
        title_exclude = set(
            x.lower() for x in cleaned_data['title_exclude'].split()
            if x.strip()
        )
        if title_include & title_exclude:
            raise forms.ValidationError(
                'Mutual overlap in title words: {}'.format(
                    ', '.join(title_include & title_exclude)
                )
            )
        # check tags
        tags_include = set(
            x.name for x in cleaned_data.get('tags_include', [])
        )
        tags_exclude = set(
            x.name for x in cleaned_data.get('tags_exclude', [])
        )
        if tags_include & tags_exclude:
            raise forms.ValidationError(
                'Mutual overlap in tags: {}'.format(
                    ', '.join(tags_include & tags_exclude)
                )
            )

        # check channels
        channels_include = set(
            x.name for x in cleaned_data.get('channels_include', [])
        )
        channels_exclude = set(
            x.name for x in cleaned_data.get('channels_exclude', [])
        )
        if channels_include & channels_exclude:
            raise forms.ValidationError(
                'Mutual overlap in channels: {}'.format(
                    ', '.join(channels_include & channels_exclude)
                )
            )

        any_data = False
        for key, value in cleaned_data.items():
            if key == 'name':
                # doesn't count
                continue
            if value:
                any_data = True
                break
        if not any_data:
            raise forms.ValidationError('Nothing entered')

        return cleaned_data

    def export_filters(self):
        assert self.cleaned_data
        assert self.is_valid()

        data = {}
        cd = self.cleaned_data

        data['title'] = {
            'include': cd['title_include'],
            'exclude': cd['title_exclude'],
        }
        data['tags'] = {
            'include': [x.id for x in cd['tags_include']],
            'exclude': [x.id for x in cd['tags_exclude']],
        }
        data['channels'] = {
            'include': [x.id for x in cd['channels_include']],
            'exclude': [x.id for x in cd['channels_exclude']],
        }
        data['privacy'] = cd['privacy']

        return data
