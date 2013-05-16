import re
import pytz

from django import forms
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.contrib.flatpages.models import FlatPage
from django.template.defaultfilters import slugify

from funfactory.urlresolvers import reverse

from airmozilla.base.forms import BaseModelForm, BaseForm
from airmozilla.manage import url_transformer
from airmozilla.main.models import (
    Approval,
    Category,
    Event,
    EventTweet,
    Location,
    Participant,
    Tag,
    Template,
    Channel,
    SuggestedEvent,
    URLMatch
)


TIMEZONE_CHOICES = [(tz, tz.replace('_', ' ')) for tz in pytz.common_timezones]


class UserEditForm(BaseModelForm):
    class Meta:
        model = User
        fields = ('is_active', 'is_staff', 'is_superuser', 'groups')

    def clean(self):
        cleaned_data = super(UserEditForm, self).clean()
        is_active = cleaned_data.get('is_active')
        is_staff = cleaned_data.get('is_staff')
        is_superuser = cleaned_data.get('is_superuser')
        groups = cleaned_data.get('groups')
        if is_superuser and not is_staff:
            raise forms.ValidationError('Superusers must be staff.')
        if is_staff and not is_active:
            raise forms.ValidationError('Staff must be active.')
        if is_staff and not is_superuser and not groups:
            raise forms.ValidationError(
                'Non-superuser staff must belong to a group.'
            )
        return cleaned_data


class GroupEditForm(BaseModelForm):
    def __init__(self, *args, **kwargs):
        super(GroupEditForm, self).__init__(*args, **kwargs)
        self.fields['name'].required = True
        choices = self.fields['permissions'].choices
        self.fields['permissions'] = forms.MultipleChoiceField(
            choices=choices,
            widget=forms.CheckboxSelectMultiple,
            required=False
        )

    class Meta:
        model = Group


class UserFindForm(BaseForm):

    email = forms.CharField(max_length=200)

    def clean_email(self):
        email = self.cleaned_data['email']
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            try:
                user = User.objects.get(email__istartswith=email)
            except User.DoesNotExist:
                raise forms.ValidationError('User with this email not found.')
        return user.email


class EventRequestForm(BaseModelForm):
    tags = forms.CharField(required=False)
    participants = forms.CharField(required=False)
    timezone = forms.ChoiceField(
        choices=TIMEZONE_CHOICES,
        initial=settings.TIME_ZONE, label='Time zone'
    )

    def __init__(self, *args, **kwargs):
        super(EventRequestForm, self).__init__(*args, **kwargs)
        self.fields['participants'].help_text = (
            '<a href="%s" class="btn" target="_blank">'
            '<i class="icon-plus-sign"></i>'
            'New Participant'
            '</a>' % reverse('manage:participant_new'))
        self.fields['location'].help_text = (
            '<a href="%s" class="btn" target="_blank">'
            '<i class="icon-plus-sign"></i>'
            'New location'
            '</a>' % reverse('manage:location_new'))
        self.fields['category'].help_text = (
            '<a href="%s" class="btn" target="_blank">'
            '<i class="icon-plus-sign"></i>'
            'New category'
            '</a>' % reverse('manage:category_new'))
        self.fields['channels'].help_text = (
            '<a href="%s" class="btn" target="_blank">'
            '<i class="icon-plus-sign"></i>'
            'New channel'
            '</a>' % reverse('manage:channel_new'))
        self.fields['placeholder_img'].label = 'Placeholder image'
        if 'instance' in kwargs:
            event = kwargs['instance']
            approvals = event.approval_set.all()
            self.initial['approvals'] = [app.group for app in approvals]
            if event.pk:
                tag_format = lambda objects: ','.join(map(unicode, objects))
                participants_formatted = tag_format(event.participants.all())
                tags_formatted = tag_format(event.tags.all())
                self.initial['tags'] = tags_formatted
                self.initial['participants'] = participants_formatted

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
        if Event.objects.filter(slug=slug).exclude(pk=self.instance.id):
            raise forms.ValidationError('This slug is already in use.')
        return slug

    @staticmethod
    def _check_flatpage_slug(slug):
        if FlatPage.objects.filter(url__startswith='/%s' % slug).count():
            raise forms.ValidationError(
                "The default slug for event would clash with an existing "
                "static page with the same URL. It might destroy existing "
                "URLs that people depend on."
            )

    def clean(self):
        data = super(EventRequestForm, self).clean()
        if data.get('title') and not data.get('slug'):
            # this means you have submitted a form without being explicit
            # about what the slug will be
            self._check_flatpage_slug(slugify(data.get('title')))
        elif data.get('slug'):
            # are you trying to change it?
            if self.instance.slug != data['slug']:
                # apparently, you want to change to a new slug
                self._check_flatpage_slug(data['slug'])
        return data

    class Meta:
        model = Event
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'short_description': forms.Textarea(attrs={'rows': 2}),
            'call_info': forms.Textarea(attrs={'rows': 3}),
            'additional_links': forms.Textarea(attrs={'rows': 3}),
            'template_environment': forms.Textarea(attrs={'rows': 3}),
            'additional_links': forms.Textarea(attrs={'rows': 3}),
            'start_time': forms.DateTimeInput(format='%Y-%m-%d %H:%M'),
            'archive_time': forms.DateTimeInput(format='%Y-%m-%d %H:%M'),
        }
        exclude = ('featured', 'status', 'archive_time', 'slug')
        # Fields specified to enforce order
        fields = (
            'title', 'placeholder_img', 'description',
            'short_description', 'location', 'start_time', 'timezone',
            'participants', 'channels', 'category', 'tags', 'call_info',
            'additional_links', 'privacy'
        )


class EventEditForm(EventRequestForm):
    approvals = forms.ModelMultipleChoiceField(
        queryset=Group.objects.filter(permissions__codename='change_approval'),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )

    class Meta(EventRequestForm.Meta):
        exclude = ('archive_time',)
        # Fields specified to enforce order
        fields = (
            'title', 'slug', 'status', 'privacy', 'featured', 'template',
            'template_environment', 'placeholder_img', 'location',
            'description', 'short_description', 'start_time', 'archive_time',
            'timezone', 'participants', 'channels', 'category', 'tags',
            'call_info', 'additional_links', 'approvals'
        )


class EventExperiencedRequestForm(EventEditForm):
    class Meta(EventEditForm.Meta):
        #widgets = EventRequestForm.Meta.widgets
        #widgets['approvals'] = forms.CheckboxSelectMultiple()
        #widgets['approvals'] = forms.Textarea()

        exclude = ('featured', 'archive_time', 'slug')
        # Fields specified to enforce order
        fields = (
            'title', 'status', 'privacy', 'template',
            'template_environment', 'placeholder_img', 'description',
            'short_description', 'location', 'start_time', 'timezone',
            'participants', 'channels', 'category', 'tags', 'call_info',
            'additional_links', 'approvals'
        )


class EventArchiveForm(BaseModelForm):
    archive_time = forms.IntegerField()

    def __init__(self, *args, **kwargs):
        super(EventArchiveForm, self).__init__(*args, **kwargs)
        self.fields['archive_time'].help_text = (
            '<div id="archive_time_slider"></div>'
        )

    class Meta(EventRequestForm.Meta):
        exclude = ()
        fields = ('template', 'template_environment')


class EventFindForm(BaseModelForm):
    class Meta:
        model = Event
        fields = ('title',)
        widgets = {
            'title': forms.TextInput(attrs={'autocomplete': 'off'})
        }

    def clean_title(self):
        title = self.cleaned_data['title']
        if not Event.objects.filter(title__icontains=title):
            raise forms.ValidationError('No event with this title found.')
        return title


class EventTweetForm(BaseModelForm):
    class Meta:
        model = EventTweet
        fields = (
            'text',
            'include_placeholder',
            'send_date',
        )
        widgets = {
            'text': forms.Textarea(attrs={
                'autocomplete': 'off',
                'data-maxlength': 140,
                'rows': 2,
            })
        }

    def __init__(self, event, *args, **kwargs):
        super(EventTweetForm, self).__init__(*args, **kwargs)
        self.fields['text'].help_text = (
            '<b class="char-counter">140</b> characters left'
        )
        # it's a NOT NULL field but it defaults to NOW()
        # in the views code
        self.fields['send_date'].required = False

        if event.tags.all():

            def pack_tags(tags):
                return '[%s]' % (','.join('"%s"' % x for x in tags))

            self.fields['text'].help_text += (
                '<br><a href="#" class="include-event-tags" '
                'data-tags=\'%s\'>include all event tags</a>'
                % pack_tags([x.name for x in event.tags.all()])
            )

        if event.placeholder_img:
            from airmozilla.main.helpers import thumbnail
            thumb = thumbnail(event.placeholder_img, '100x100')

            #from sorl.thumbnail import get_thumbnail
            self.fields['include_placeholder'].help_text = (
                '<img src="%(url)s" alt="placeholder" class="thumbnail" '
                'width="%(width)s" width="%(height)s">' %
                {
                    'url': thumb.url,
                    'width': thumb.width,
                    'height': thumb.height
                }
            )
        else:
            del self.fields['include_placeholder']

        if event.location:
            self.fields['send_date'].help_text = (
                'Timezone is %s' % event.location.timezone
            )


class ParticipantEditForm(BaseModelForm):
    class Meta:
        model = Participant
        exclude = ('creator', 'clear_token')


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


class ChannelForm(BaseModelForm):
    class Meta:
        model = Channel
        exclude = ('created',)


class TemplateEditForm(BaseModelForm):
    class Meta:
        model = Template
        widgets = {
            'content': forms.Textarea(attrs={'rows': 20})
        }


class LocationEditForm(BaseModelForm):
    timezone = forms.ChoiceField(choices=TIMEZONE_CHOICES)

    def __init__(self, *args, **kwargs):
        super(LocationEditForm, self).__init__(*args, **kwargs)
        if 'instance' in kwargs:
            initial = kwargs['instance'].timezone
        else:
            initial = settings.TIME_ZONE
        self.initial['timezone'] = initial

    class Meta:
        model = Location


class ApprovalForm(BaseModelForm):
    class Meta:
        model = Approval
        fields = ('comment',)
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3})
        }


class FlatPageEditForm(BaseModelForm):
    class Meta:
        model = FlatPage
        fields = ('url', 'title', 'content')

    def clean_url(self):
        value = self.cleaned_data['url']
        if value.startswith('sidebar'):
            # expect it to be something like
            # 'sidebar_bottom_how-tos'
            try:
                __, __, channel_slug = value.split('_', 2)
            except ValueError:
                raise forms.ValidationError(
                    "Must be format like `sidebar_bottom_channel-slug`"
                )
            try:
                Channel.objects.get(slug=channel_slug)
            except Channel.DoesNotExist:
                raise forms.ValidationError(
                    "No channel slug found called `%s`" % channel_slug
                )

        return value


class VidlyURLForm(forms.Form):
    url = forms.CharField(
        required=True,
        label='URL',
        widget=forms.widgets.TextInput(attrs={
            'placeholder': 'E.g. http://videos.mozilla.org/.../file.flv',
            'class': 'input-xxlarge',
        })
    )
    email = forms.EmailField(
        required=False,
        help_text="To send you a notification when it's complete"
    )
    token_protection = forms.BooleanField(required=False)
    hd = forms.BooleanField(required=False, label='HD')

    def __init__(self, *args, **kwargs):
        disable_token_protection = kwargs.pop(
            'disable_token_protection',
            False
        )
        super(VidlyURLForm, self).__init__(*args, **kwargs)
        if disable_token_protection:
            self.fields['token_protection'].widget.attrs['disabled'] = (
                'disabled'
            )
            self.fields['token_protection'].required = True
            self.fields['token_protection'].help_text = (
                'Required for non-public events'
            )

    def clean_url(self):
        # annoyingly, we can't use forms.URLField since it barfs on
        # Basic Auth urls. Instead, let's just make some basic validation
        # here
        value = self.cleaned_data['url']
        if ' ' in value or '://' not in value:
            raise forms.ValidationError('Not a valid URL')
        value, error = url_transformer.run(value)
        if error:
            raise forms.ValidationError(error)
        return value


class EventsAutocompleteForm(BaseForm):

    q = forms.CharField(required=True, max_length=200)
    max = forms.IntegerField(required=False, min_value=1, max_value=20)


class AcceptSuggestedEventForm(BaseModelForm):

    class Meta:
        model = SuggestedEvent
        fields = ('review_comments',)


class TagEditForm(BaseModelForm):

    class Meta:
        model = Tag

    def clean_name(self):
        name = self.cleaned_data['name']
        if Tag.objects.filter(name__iexact=name).exclude(pk=self.instance.pk):
            raise forms.ValidationError("Tag already in use")
        return name


class VidlyResubmitForm(VidlyURLForm):
    id = forms.IntegerField(widget=forms.widgets.HiddenInput())


class URLMatchForm(BaseModelForm):

    class Meta:
        model = URLMatch
        exclude = ('use_count',)

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if URLMatch.objects.filter(name__iexact=name):
            raise forms.ValidationError("URL matcher name already in use")
        return name

    def clean_string(self):
        string = self.cleaned_data['string']
        try:
            re.compile(string)
        except Exception as e:
            raise forms.ValidationError(e)
        return string
