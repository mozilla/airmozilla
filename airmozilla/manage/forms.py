from django import forms
from django.contrib.auth.models import User, Group


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('is_active', 'is_staff', 'is_superuser',
                  'groups', 'user_permissions')


class GroupEditForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(GroupEditForm, self).__init__(*args, **kwargs)
        self.fields['name'].required = True
        choices = self.fields['permissions'].choices
        self.fields['permissions'] = forms.MultipleChoiceField(choices=choices,
                                           widget=forms.CheckboxSelectMultiple,
                                           required=False)

    class Meta:
        model = Group


class UserFindForm(forms.ModelForm):
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
