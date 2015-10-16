import requests

from django import forms
from django.conf import settings
from django.db.models import Q
from django.core.urlresolvers import reverse

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
from . import utils


class StartForm(BaseModelForm):

    event_type = forms.ChoiceField(
        label='What kind of event is this?',
        choices=[
            ('upcoming', 'Upcoming'),
            ('popcorn', 'Popcorn')
        ],
        widget=forms.widgets.RadioSelect()
    )

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


class PopcornForm(BaseModelForm):

    class Meta:
        model = SuggestedEvent
        fields = ('popcorn_url',)

    def __init__(self, *args, **kwargs):
        super(PopcornForm, self).__init__(*args, **kwargs)
        self.fields['popcorn_url'].label = 'Popcorn URL'

    def clean_popcorn_url(self):
        url = self.cleaned_data['popcorn_url']
        if '://' not in url:
            url = 'http://' + url
        response = requests.get(url)
        if response.status_code != 200:
            raise forms.ValidationError('URL can not be found')
        return url


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

    tags = forms.CharField(required=False)

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
        super(DetailsForm, self).__init__(*args, **kwargs)
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

        if not self.instance.upcoming:
            del self.fields['location']
            del self.fields['start_time']
            del self.fields['remote_presenters']
            del self.fields['call_info']
        else:
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
            if event.pk:
                tags_formatted = ','.join(x.name for x in event.tags.all())
                self.initial['tags'] = tags_formatted

                if event.location:
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

    def clean_tags(self):
        tags = self.cleaned_data['tags']
        split_tags = [t.strip() for t in tags.split(',') if t.strip()]
        final_tags = []
        for tag_name in split_tags:
            t, __ = Tag.objects.get_or_create(name=tag_name)
            final_tags.append(t)
        return final_tags

    def clean_channels(self):
        channels = self.cleaned_data['channels']
        if not channels:
            return Channel.objects.filter(slug=settings.DEFAULT_CHANNEL_SLUG)
        return channels


class DiscussionForm(BaseModelForm):

    emails = forms.CharField(required=False, label="Moderators")

    class Meta:
        model = SuggestedDiscussion
        fields = ('enabled', 'moderate_all')

    def __init__(self, *args, **kwargs):
        super(DiscussionForm, self).__init__(*args, **kwargs)
        self.fields['moderate_all'].help_text = (
            'That every comment has to be approved before being shown '
            'publically. '
        )
        self.fields['emails'].widget.attrs.update({
            'data-autocomplete-url': reverse('suggest:autocomplete_emails')
        })

    def clean_emails(self):
        value = self.cleaned_data['emails']
        emails = list(set([
            x.lower().strip() for x in value.split(',') if x.strip()
        ]))
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
