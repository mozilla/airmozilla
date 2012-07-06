from django import forms
from django.contrib.auth.models import User, Group

from funfactory.urlresolvers import reverse

from airmozilla.base.forms import BaseModelForm
from airmozilla.main.models import (Category, Event, EventOldSlug,
                                    Participant, Tag, Template)


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
    participants = forms.CharField()

    def __init__(self, *args, **kwargs):
        super(EventRequestForm, self).__init__(*args, **kwargs)
        self.fields['participants'].help_text = (
             '<a href="%s" class="btn" target="_blank">'
             '<i class="icon-plus-sign"></i>'
             'New Participant'
             '</a>' % reverse('manage:participant_new'))

    def clean_tags(self):
        tags = self.cleaned_data['tags']
        split_tags = [t.strip() for t in tags.split(',') if t.strip()]
        final_tags = []
        for tag_name in split_tags:
            t, __ = Tag.objects.get_or_create(name=tag_name)
            final_tags.append(t)
        return final_tags

    def clean_participants(self):
        participants = self.cleaned_data['participants']
        split_participants = [p.strip() for p in participants.split(',')
                              if p.strip()]
        final_participants = []
        for participant_name in split_participants:
            p = Participant.objects.get(name=participant_name)
            final_participants.append(p)
        return final_participants

    def clean_slug(self):
        """Enforce unique slug across current slugs and old slugs."""
        slug = self.cleaned_data['slug']
        if (Event.objects.filter(slug=slug).exclude(pk=self.instance.id)
                  or EventOldSlug.objects.filter(slug=slug)):
            raise forms.ValidationError('This slug is already in use.')
        return slug

    class Meta:
        model = Event
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'short_description': forms.Textarea(attrs={'rows': 2}),
            'call_info': forms.Textarea(attrs={'rows': 3}),
            'additional_links': forms.Textarea(attrs={'rows': 3}),
            'template_environment': forms.Textarea(attrs={'rows': 3})
        }
        exclude = ('featured', 'status', 'archive_time')


class EventEditForm(EventRequestForm):
    class Meta:
        model = Event
        widgets = EventRequestForm._meta.widgets
        exclude = ()


class EventFindForm(BaseModelForm):
    class Meta:
        model = Event
        fields = ('title',)

    def clean_title(self):
        title = self.cleaned_data['title']
        if not Event.objects.filter(title__icontains=title):
            raise forms.ValidationError('No event with this title found.')
        return title


class ParticipantEditForm(BaseModelForm):
    class Meta:
        model = Participant


class ParticipantFindForm(BaseModelForm):
    class Meta:
        model = Participant
        fields = ('name',)

    def clean_name(self):
        name = self.cleaned_data['name']
        if not Participant.objects.filter(name__icontains=name):
            raise forms.ValidationError('No participant with this name found.')
        return name


class CategoryForm(BaseModelForm):
    class Meta:
        model = Category


class TemplateEditForm(BaseModelForm):
    class Meta:
        model = Template
        widgets = {
            'content': forms.Textarea(attrs={'rows': 20})
        }
