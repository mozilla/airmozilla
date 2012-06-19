from django import forms
from django.contrib.auth.models import User, Group

from airmozilla.base.forms import BaseModelForm 
from airmozilla.main.models import Category, Event, Tag


class UserEditForm(BaseModelForm):
    class Meta:
        model = User
        fields = ('is_active', 'is_staff', 'is_superuser',
                  'groups', 'user_permissions')


class GroupEditForm(BaseModelForm):
    def __init__(self, *args, **kwargs):
        super(GroupEditForm, self).__init__(*args, **kwargs)
        self.fields['name'].required = True
        choices = self.fields['permissions'].choices
        self.fields['permissions'] = forms.MultipleChoiceField(choices=choices,
                                           widget=forms.CheckboxSelectMultiple,
                                           required=False)

    class Meta:
        model = Group


class UserFindForm(BaseModelForm):
    class Meta:
        model = User
        fields = ('email',)

    def clean_email(self):
        email = self.cleaned_data['email']
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise forms.ValidationError('User with this email not found.')
        return user.email


class EventRequestForm(BaseModelForm):
    tags = forms.CharField()

    def clean_tags(self):
        tags = self.cleaned_data['tags']
        split_tags = tags.split(',')
        final_tags = []
        for tag_name in split_tags:
            tag_name = tag_name.strip()
            if tag_name:
                t, __ = Tag.objects.get_or_create(name=tag_name)
                final_tags.append(t)
        return final_tags

    class Meta:
        model = Event
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'call_info': forms.Textarea(attrs={'rows': 3}),
            'additional_links': forms.Textarea(attrs={'rows': 3})
        }

class CategoryForm(BaseModelForm):
    class Meta:
        model = Category
