from django import forms


class _BaseForm(object):
    def clean(self):
        cleaned_data = super(_BaseForm, self).clean()
        for field in cleaned_data:
            if isinstance(cleaned_data[field], basestring):
                cleaned_data[field] = (
                    cleaned_data[field].replace('\r\n', '\n')
                    .replace(u'\u2018', "'").replace(u'\u2019', "'").strip())

        return cleaned_data


class BaseModelForm(_BaseForm, forms.ModelForm):
    pass


class BaseForm(_BaseForm, forms.Form):
    pass
