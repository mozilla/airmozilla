import re
import pytz

from django import forms
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.contrib.flatpages.models import FlatPage
from django.utils.timezone import utc
from funfactory.urlresolvers import reverse

from slugify import slugify

from airmozilla.base.forms import BaseModelForm, BaseForm
from airmozilla.manage import url_transformer
from airmozilla.main.models import (
    Approval,
    Event,
    EventTweet,
    Location,
    Participant,
    Tag,
    Template,
    Channel,
    SuggestedEvent,
    SuggestedEventComment,
    URLMatch,
    EventAssignment,
    LocationDefaultEnvironment
)
from airmozilla.comments.models import Discussion, Comment


TIMEZONE_CHOICES = [(tz, tz.replace('_', ' ')) for tz in pytz.common_timezones]

ONE_HOUR = 60 * 60


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
        if not User.objects.filter(email__icontains=email):
            raise forms.ValidationError('No users found')
        return email


class EventRequestForm(BaseModelForm):
    tags = forms.CharField(required=False)
    participants = forms.CharField(required=False)

    class Meta:
        model = Event
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'short_description': forms.Textarea(attrs={'rows': 2}),
            'call_info': forms.Textarea(attrs={'rows': 3}),
            'additional_links': forms.Textarea(attrs={'rows': 3}),
            'template_environment': forms.Textarea(attrs={'rows': 3}),
            'additional_links': forms.Textarea(attrs={'rows': 3}),
            'remote_presenters': forms.Textarea(attrs={'rows': 3}),
            'start_time': forms.DateTimeInput(format='%Y-%m-%d %H:%M'),
            'archive_time': forms.DateTimeInput(format='%Y-%m-%d %H:%M'),
        }
        exclude = ('featured', 'status', 'archive_time', 'slug')
        # Fields specified to enforce order
        fields = (
            'title', 'placeholder_img', 'description',
            'short_description', 'location', 'start_time',
            'participants', 'channels', 'tags', 'call_info',
            'remote_presenters',
            'additional_links', 'privacy', 'popcorn_url'
        )

    def __init__(self, *args, **kwargs):
        super(EventRequestForm, self).__init__(*args, **kwargs)
        self.fields['participants'].help_text = (
            '<a href="%s" class="btn btn-default" target="_blank">'
            '<i class="glyphicon glyphicon-plus-sign"></i>'
            'New Participant'
            '</a>' % reverse('manage:participant_new'))
        self.fields['location'].help_text = (
            '<a href="%s" class="btn btn-default" target="_blank">'
            '<i class="glyphicon glyphicon-plus-sign"></i>'
            'New location'
            '</a>' % reverse('manage:location_new'))
        self.fields['channels'].help_text = (
            '<a href="%s" class="btn btn-default" target="_blank">'
            '<i class="glyphicon glyphicon-plus-sign"></i>'
            'New channel'
            '</a>' % reverse('manage:channel_new'))
        self.fields['placeholder_img'].label = 'Placeholder image'
        if 'instance' in kwargs:
            event = kwargs['instance']
            approvals = event.approval_set.all()
            self.initial['approvals'] = [app.group for app in approvals]
            if event.location:
                # when the django forms present the start_time form field,
                # it's going to first change it to UTC, then strftime it
                self.initial['start_time'] = (
                    event.location_time.replace(tzinfo=utc)
                )

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
            try:
                t = Tag.objects.get(name=tag_name)
            except Tag.DoesNotExist:
                try:
                    t = Tag.objects.get(name__iexact=tag_name)
                except Tag.DoesNotExist:
                    t = Tag.objects.create(name=tag_name)
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
            self._check_flatpage_slug(slugify(data.get('title')).lower())
        elif data.get('slug'):
            # are you trying to change it?
            if self.instance.slug != data['slug']:
                # apparently, you want to change to a new slug
                self._check_flatpage_slug(data['slug'])
        return data


class EventEditForm(EventRequestForm):
    approvals = forms.ModelMultipleChoiceField(
        queryset=Group.objects.filter(permissions__codename='change_approval'),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )
    curated_groups = forms.CharField(
        required=False,
        help_text='Curated groups only matter if the event is open to'
                  ' "%s".' % [x[1] for x in Event.PRIVACY_CHOICES
                              if x[0] == Event.PRIVACY_CONTRIBUTORS][0]
    )

    class Meta(EventRequestForm.Meta):
        exclude = ('archive_time',)
        # Fields specified to enforce order
        fields = (
            'title', 'slug', 'status', 'privacy', 'featured', 'template',
            'template_environment', 'placeholder_img', 'location',
            'description', 'short_description', 'start_time', 'archive_time',
            'participants', 'channels', 'tags',
            'call_info', 'additional_links', 'remote_presenters',
            'approvals',
            'popcorn_url',
            'pin',
        )

    def __init__(self, *args, **kwargs):
        super(EventEditForm, self).__init__(*args, **kwargs)
        if 'pin' in self.fields:
            self.fields['pin'].help_text = (
                "Use of pins is deprecated. Use Curated groups instead."
            )
        self.fields['popcorn_url'].label = 'Popcorn URL'

    def clean_pin(self):
        value = self.cleaned_data['pin']
        if value and len(value) < 4:
            raise forms.ValidationError("Pin too short to be safe")
        return value


class EventExperiencedRequestForm(EventEditForm):

    class Meta(EventEditForm.Meta):

        exclude = ('featured', 'archive_time', 'slug')
        # Fields specified to enforce order
        fields = (
            'title', 'status', 'privacy', 'template',
            'template_environment', 'placeholder_img', 'description',
            'short_description', 'location', 'start_time',
            'participants', 'channels', 'tags', 'call_info',
            'additional_links', 'remote_presenters',
            'approvals', 'pin', 'popcorn_url',
        )


class EventArchiveForm(BaseModelForm):

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


class ChannelForm(BaseModelForm):
    class Meta:
        model = Channel
        exclude = ('created',)

    def __init__(self, *args, **kwargs):
        super(ChannelForm, self).__init__(*args, **kwargs)
        self.fields['parent'].required = False
        if kwargs.get('instance'):
            self.fields['parent'].choices = [
                (x, y) for (x, y)
                in self.fields['parent'].choices
                if x != kwargs['instance'].pk
            ]


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


class LocationDefaultEnvironmentForm(BaseModelForm):

    class Meta:
        model = LocationDefaultEnvironment
        fields = ('privacy', 'template', 'template_environment')


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
        widgets = {
            'review_comments': forms.Textarea(attrs={'rows': 3})
        }


class TagEditForm(BaseModelForm):

    class Meta:
        model = Tag

    def clean_name(self):
        name = self.cleaned_data['name']
        if Tag.objects.filter(name__iexact=name).exclude(pk=self.instance.pk):
            raise forms.ValidationError("Tag already in use")
        return name


class TagMergeForm(BaseForm):

    name = forms.ChoiceField(
        label='Name to keep',
        widget=forms.widgets.RadioSelect()
    )

    def __init__(self, name, *args, **kwargs):
        super(TagMergeForm, self).__init__(*args, **kwargs)

        def describe_tag(tag):
            count = Event.objects.filter(tags=tag).count()
            if count == 1:
                tmpl = '%s (%d time)'
            else:
                tmpl = '%s (%d times)'
            return tmpl % (tag.name, count)

        self.fields['name'].choices = [
            (x.name, describe_tag(x))
            for x in Tag.objects.filter(name__iexact=name)
        ]


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


class SuggestedEventCommentForm(BaseModelForm):

    class Meta:
        model = SuggestedEventComment
        fields = ('comment',)
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3})
        }


class DiscussionForm(BaseModelForm):

    class Meta:
        model = Discussion
        fields = ('enabled', 'closed', 'moderate_all', 'notify_all',
                  'moderators')


class CommentEditForm(BaseModelForm):

    class Meta:
        model = Comment
        fields = ('status', 'comment', 'flagged')


class CommentsFilterForm(BaseForm):

    user = forms.CharField(required=False)
    comment = forms.CharField(required=False)
    status = forms.ChoiceField(
        required=False,
        choices=(
            (('', 'ALL'),) + Comment.STATUS_CHOICES + (('flagged', 'Flagged'),)
        )
    )


class CommentsFilterForm(CommentsFilterForm):

    event = forms.CharField(required=False)


class EventAssignmentForm(BaseModelForm):

    class Meta:
        model = EventAssignment
        fields = ('locations', 'users')

    def __init__(self, *args, **kwargs):
        super(EventAssignmentForm, self).__init__(*args, **kwargs)
        users = (
            User.objects
            .extra(select={
                'email_lower': 'LOWER(email)'
            })
            .filter(is_active=True)
            .order_by('email_lower')
        )

        def describe_user(user):
            ret = user.email
            if user.first_name or user.last_name:
                name = (user.first_name + ' ' + user.last_name).strip()
                ret += ' (%s)' % name
            return ret

        self.fields['users'].choices = [
            (x.pk, describe_user(x)) for x in users
        ]
        self.fields['users'].required = False
        self.fields['users'].help_text = 'Start typing to find users.'

        locations = (
            Location.objects.all()
            .order_by('name')
        )
        if self.instance.event.location:
            locations = locations.exclude(pk=self.instance.event.location.pk)
        self.fields['locations'].choices = [
            (x.pk, x.name) for x in locations
        ]
        self.fields['locations'].required = False
        self.fields['locations'].help_text = 'Start typing to find locations.'


class EventTranscriptForm(BaseModelForm):

    class Meta:
        model = Event
        fields = ('transcript', )
