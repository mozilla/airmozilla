from django import forms
from django.conf import settings
from django.db.models import Q
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from slugify import slugify

from airmozilla.base.forms import BaseModelForm, GallerySelect
from airmozilla.main.models import (
    SuggestedEvent,
    Event,
    Tag,
    Channel,
    SuggestedEventComment
)
from airmozilla.comments.models import SuggestedDiscussion
from airmozilla.main.forms import TagsModelMultipleChoiceField
from . import utils


class StartForm(BaseModelForm):

    class Meta:
        model = SuggestedEvent
        fields = ('title',)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(StartForm, self).__init__(*args, **kwargs)


class TitleForm(BaseModelForm):

    class Meta:
        model = SuggestedEvent
        fields = ('title', 'slug')

    def clean_slug(self):
        value = self.cleaned_data['slug']
        if value:
            if Event.objects.filter(slug__iexact=value):
                raise forms.ValidationError('Already taken')
        return value

    def clean(self):
        cleaned_data = super(TitleForm, self).clean()
        if 'slug' in cleaned_data and 'title' in cleaned_data:
            if not cleaned_data['slug']:
                cleaned_data['slug'] = slugify(cleaned_data['title']).lower()
                if Event.objects.filter(slug=cleaned_data['slug']):
                    raise forms.ValidationError('Slug already taken')
        return cleaned_data


class DescriptionForm(BaseModelForm):

    class Meta:
        model = SuggestedEvent
        fields = ('description', 'short_description')

    def __init__(self, *args, **kwargs):
        super(DescriptionForm, self).__init__(*args, **kwargs)
        self.fields['description'].help_text = (
            "Write a description of your event that will entice viewers to "
            "watch.&lt;br&gt;"
            "An interesting description improves the chances of your "
            "presentation being picked up by bloggers and other websites."
            "&lt;br&gt;"
            "Please phrase your description in the present tense. "
        )
        self.fields['short_description'].label += ' (optional)'
        self.fields['short_description'].help_text = (
            "This Short Description is used in public feeds and tweets.  "
            "&lt;br&gt;If your event is non-public be careful "
            "&lt;b&gt;not to "
            "disclose sensitive information here&lt;/b&gt;."
            "&lt;br&gt;If left blank the system will use the first few "
            "words of the description above."
        )


class DetailsForm(BaseModelForm):

    tags = TagsModelMultipleChoiceField(
        Tag.objects.all(),
        required=False,
    )

    enable_discussion = forms.BooleanField(required=False)

    class Meta:
        model = SuggestedEvent
        fields = (
            'location',
            'call_info',
            'start_time',
            'estimated_duration',
            'privacy',
            'tags',
            'channels',
            'additional_links',
            'remote_presenters',
            'topics',
        )
        widgets = {
            'topics': forms.widgets.CheckboxSelectMultiple(),
            'estimated_duration': forms.widgets.Select(
                choices=Event.ESTIMATED_DURATION_CHOICES
            ),

        }

    def __init__(self, *args, **kwargs):
        no_tag_choices = kwargs.pop('no_tag_choices', None)
        super(DetailsForm, self).__init__(*args, **kwargs)

        if no_tag_choices:
            self.fields['tags'].queryset = self.instance.tags.all()
        self.fields['channels'].required = False
        self.fields['channels'].queryset = (
            Channel.objects
            .filter(
                Q(never_show=False) | Q(id__in=self.instance.channels.all())
            )
        )
        self.fields['topics'].queryset = self.fields['topics'].queryset.filter(
            is_active=True
        )
        self.fields['topics'].label = 'Topics (if any)'
        self.fields['topics'].required = False

        self.fields['location'].required = True
        self.fields['start_time'].required = True
        self.fields['location'].help_text = (
            "Choose an Air Mozilla origination point. &lt;br&gt;"
            "If the location of your event isn't on the list, "
            "choose Live Remote.  &lt;br&gt;"
            "Note that live remote dates and times are UTC."
        )
        self.fields['remote_presenters'].help_text = (
            "If there will be presenters who present remotely, please "
            "enter email addresses, names and locations about these "
            "presenters."
        )
        self.fields['remote_presenters'].widget.attrs['rows'] = 3
        self.fields['call_info'].widget = forms.widgets.TextInput()
        self.fields['call_info'].label = 'Vidyo room (if any)'
        self.fields['call_info'].help_text = (
            "If you're using a Vidyo room, which one?&lt;br&gt;"
            "Required for Cyberspace events."
        )

        # The list of available locations should only be those that are
        # still active. However, if you have a previously chosen location
        # that is now inactive, it should still be available
        location_field_q = Q(is_active=True)
        if 'instance' in kwargs:
            event = kwargs['instance']
            if event.pk and event.location:
                location_field_q |= Q(pk=event.location.pk)
        if 'location' in self.fields:
            self.fields['location'].queryset = (
                self.fields['location'].queryset.filter(location_field_q)
            )

        self.fields['tags'].label = 'Tags (Keywords that describe the event)'
        self.fields['tags'].help_text = (
            "Enter some keywords to help viewers find the recording of your "
            "event. &lt;br&gt;Press return between keywords"
        )
        self.fields['channels'].help_text = (
            "Should your event appear in one or more particular "
            "Air Mozilla Channels? &lt;br&gt;If in doubt, select Main."
        )
        self.fields['additional_links'].help_text = (
            "If you have links to slides, the presenter's blog, or other "
            "relevant links, list them here and they will appear on "
            "the event page."
        )

        self.fields['additional_links'].widget.attrs['rows'] = 3

    def clean_channels(self):
        channels = self.cleaned_data['channels']
        if not channels:
            return Channel.objects.filter(slug=settings.DEFAULT_CHANNEL_SLUG)
        return channels


class EmailsMultipleChoiceField(forms.MultipleChoiceField):

    def clean(self, value):
        emails = []
        dups = set()
        for email in value:
            email = email.strip()
            if email.lower() in dups:
                continue
            dups.add(email.lower())
            if not email:
                continue
            if not utils.is_valid_email(email):
                raise forms.ValidationError(
                    '%s is not a valid email address' % (email,)
                )
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                continue
            emails.append(user.email)
        return super(EmailsMultipleChoiceField, self).clean(emails)


class DiscussionForm(BaseModelForm):

    emails = EmailsMultipleChoiceField(
        required=False,
    )

    class Meta:
        model = SuggestedDiscussion
        fields = ('enabled', 'moderate_all')

    def __init__(self, *args, **kwargs):
        all_emails = kwargs.pop('all_emails', False)
        super(DiscussionForm, self).__init__(*args, **kwargs)
        if all_emails:
            self.fields['emails'].choices = [
                (x.email, x.email)
                for x in User.objects.filter(is_active=True)
            ]
        else:
            self.fields['emails'].choices = [
                (x.email, x.email)
                for x in self.instance.moderators.all()
            ]
        self.fields['moderate_all'].help_text = (
            'That every comment has to be approved before being shown '
            'publically. '
        )
        self.fields['emails'].widget.attrs.update({
            'data-autocomplete-url': reverse('suggest:autocomplete_emails')
        })

    def clean_emails(self):
        emails = self.cleaned_data['emails']
        for email in emails:
            if not utils.is_valid_email(email):
                raise forms.ValidationError(
                    '%s is not a valid email address' % (email,)
                )
        return emails


class PlaceholderForm(BaseModelForm):

    class Meta:
        model = SuggestedEvent
        fields = ('placeholder_img', 'picture')

    def __init__(self, *args, **kwargs):
        super(PlaceholderForm, self).__init__(*args, **kwargs)
        self.fields['placeholder_img'].label = (
            'Upload a picture from your computer'
        )
        self.fields['placeholder_img'].help_text = (
            "We need a placeholder image for your event. &lt;br&gt;"
            "A recent head-shot of the speaker is preferred. &lt;br&gt;"
            "Placeholder images should be 200 x 200 px or larger."
        )
        self.fields['picture'].widget = GallerySelect()
        self.fields['picture'].label = (
            'Select an existing picture from the gallery'
        )

    def clean(self):
        cleaned_data = super(PlaceholderForm, self).clean()
        placeholder_img = cleaned_data.get('placeholder_img')
        picture = cleaned_data.get('picture')
        if not placeholder_img and not picture:
            raise forms.ValidationError('Events needs to have a picture')
        return cleaned_data


class SuggestedEventCommentForm(BaseModelForm):

    class Meta:
        model = SuggestedEventComment
        fields = ('comment',)
