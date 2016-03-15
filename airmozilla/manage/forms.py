import re
import datetime
from collections import defaultdict

import dateutil.parser
import pytz

from django import forms
from django.db.models import Count
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.utils.timezone import utc
from django.utils.safestring import mark_safe
from django.core.urlresolvers import reverse

from slugify import slugify

from airmozilla.base.forms import BaseModelForm, BaseForm
from airmozilla.manage import url_transformer
from airmozilla.main.models import (
    Approval,
    Event,
    EventTweet,
    Location,
    Region,
    Tag,
    Template,
    Channel,
    SuggestedEvent,
    SuggestedEventComment,
    URLMatch,
    EventAssignment,
    LocationDefaultEnvironment,
    RecruitmentMessage,
    Picture,
    Topic,
    Chapter,
    CuratedGroup,
)
from airmozilla.comments.models import Discussion, Comment
from airmozilla.surveys.models import Question, Survey
from airmozilla.staticpages.models import StaticPage
from airmozilla.base.templatetags.jinja_helpers import show_duration_compact
from airmozilla.main.forms import TagsModelMultipleChoiceField

from .widgets import PictureWidget

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
        fields = ('name', 'permissions')


class EventRequestForm(BaseModelForm):
    tags = TagsModelMultipleChoiceField(
        Tag.objects.all(),
        required=False,
    )

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
            'estimated_duration': forms.widgets.Select(
                choices=Event.ESTIMATED_DURATION_CHOICES
            ),
        }
        exclude = ('featured', 'status', 'archive_time', 'slug')
        # Fields specified to enforce order
        fields = (
            'title', 'placeholder_img', 'picture',
            'description',
            'short_description', 'location', 'start_time',
            'estimated_duration',
            'channels', 'tags', 'call_info',
            'remote_presenters',
            'additional_links', 'privacy', 'popcorn_url'
        )

    def __init__(self, *args, **kwargs):
        self.curated_groups_choices = kwargs.pop('curated_groups_choices', [])
        super(EventRequestForm, self).__init__(*args, **kwargs)
        self.fields['channels'].help_text = (
            '<a href="%s" class="btn btn-default" target="_blank">'
            '<i class="glyphicon glyphicon-plus-sign"></i>'
            'New channel'
            '</a>' % reverse('manage:channel_new'))
        self.fields['placeholder_img'].label = 'Placeholder image'
        self.fields['tags'].help_text = ''
        if 'instance' in kwargs:
            event = kwargs['instance']
            approvals = event.approval_set.all()
            self.initial['approvals'] = [app.group for app in approvals]
            if event.location:
                self.fields['start_time'].help_text = (
                    'Time zone of this date is that of {0}.'.format(
                        event.location.timezone
                    )
                )
                # when the django forms present the start_time form field,
                # it's going to first change it to UTC, then strftime it
                self.initial['start_time'] = (
                    event.location_time.replace(tzinfo=utc)
                )
            else:
                self.fields['start_time'].help_text = (
                    'Since there is no location, time zone of this date '
                    ' is UTC.'
                )

    def clean_slug(self):
        """Enforce unique slug across current slugs and old slugs."""
        slug = self.cleaned_data['slug']
        if Event.objects.filter(slug=slug).exclude(pk=self.instance.id):
            raise forms.ValidationError('This slug is already in use.')
        return slug

    @staticmethod
    def _check_staticpage_slug(slug):
        if StaticPage.objects.filter(url__startswith='/%s' % slug).count():
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
            self._check_staticpage_slug(slugify(data.get('title')).lower())
        elif data.get('slug'):
            # are you trying to change it?
            if self.instance.slug != data['slug']:
                # apparently, you want to change to a new slug
                self._check_staticpage_slug(data['slug'])
        return data


class CuratedGroupsChoiceField(forms.MultipleChoiceField):
    """The purpose of this overridden field is so that we can create
    CuratedGroup objects if need be.
    """

    def clean(self, value):
        if self.event.id:
            for name in value:
                CuratedGroup.objects.get_or_create(
                    event=self.event,
                    name=name
                )
        return value


class EventEditForm(EventRequestForm):
    approvals = forms.ModelMultipleChoiceField(
        queryset=Group.objects.filter(permissions__codename='change_approval'),
        required=False,
        widget=forms.CheckboxSelectMultiple()
    )
    curated_groups = CuratedGroupsChoiceField(
        required=False,
        help_text='Curated groups only matter if the event is open to'
                  ' "%s".' % [x[1] for x in Event.PRIVACY_CHOICES
                              if x[0] == Event.PRIVACY_CONTRIBUTORS][0],
    )

    class Meta(EventRequestForm.Meta):
        exclude = ('archive_time',)
        # Fields specified to enforce order
        fields = (
            'title', 'slug', 'status', 'privacy', 'curated_groups',
            'featured', 'template',
            'template_environment', 'placeholder_img', 'picture',
            'location',
            'description', 'short_description', 'start_time',
            'estimated_duration',
            'archive_time',
            'channels', 'tags',
            'call_info', 'additional_links', 'remote_presenters',
            'approvals',
            'popcorn_url',
            'pin',
            'recruitmentmessage',
        )

    def __init__(self, *args, **kwargs):
        super(EventEditForm, self).__init__(*args, **kwargs)

        # This is important so that the clean() method on this field
        # can create new CuratedGroup records if need be.
        self.fields['curated_groups'].event = self.instance
        self.fields['curated_groups'].choices = self.curated_groups_choices

        if 'pin' in self.fields:
            self.fields['pin'].help_text = (
                "Use of pins is deprecated. Use Curated groups instead."
            )
        self.fields['popcorn_url'].label = 'Popcorn URL'
        if 'recruitmentmessage' in self.fields:
            self.fields['recruitmentmessage'].required = False
            self.fields['recruitmentmessage'].label = 'Recruitment message'

        self.fields['location'].queryset = (
            Location.objects.filter(is_active=True).order_by('name')
        )
        if self.instance and self.instance.id:
            # Checking for id because it might be an instance but never
            # been saved before.
            self.fields['picture'].widget = PictureWidget(self.instance)
            # make the list of approval objects depend on requested approvals
            # print Group.approval_set.filter(event=self.instance)
            group_ids = [
                x[0] for x in
                Approval.objects
                .filter(event=self.instance).values_list('group')
            ]
            self.fields['approvals'].queryset = Group.objects.filter(
                id__in=group_ids
            )
            # If the event has a duration, it doesn't make sense to
            # show the estimated_duration widget.
            if self.instance.duration:
                del self.fields['estimated_duration']
        elif self.initial.get('picture'):
            self.fields['picture'].widget = PictureWidget(
                Picture.objects.get(id=self.initial['picture']),
                editable=False
            )
        else:
            # too early to associate with a picture
            del self.fields['picture']

    def clean_pin(self):
        value = self.cleaned_data['pin']
        if value and len(value) < 4:
            raise forms.ValidationError("Pin too short to be safe")
        return value

    def clean(self):
        cleaned_data = super(EventEditForm, self).clean()
        if not (
            cleaned_data.get('placeholder_img') or cleaned_data.get('picture')
        ):
            raise forms.ValidationError("Must have a placeholder or a Picture")
        return cleaned_data


class EventExperiencedRequestForm(EventEditForm):

    class Meta(EventEditForm.Meta):

        exclude = ('featured', 'archive_time', 'slug')
        # Fields specified to enforce order
        fields = (
            'title', 'status', 'privacy', 'template',
            'template_environment', 'placeholder_img', 'picture',
            'description',
            'short_description', 'location', 'start_time',
            'estimated_duration',
            'channels', 'tags', 'call_info',
            'additional_links', 'remote_presenters',
            'approvals', 'pin', 'popcorn_url', 'recruitmentmessage'
        )


class EventArchiveForm(BaseModelForm):

    class Meta(EventRequestForm.Meta):
        exclude = ()
        fields = ('template', 'template_environment')


class EventArchiveTimeForm(BaseModelForm):

    class Meta(EventRequestForm.Meta):
        exclude = ()
        fields = ('archive_time',)

    def __init__(self, *args, **kwargs):
        super(EventArchiveTimeForm, self).__init__(*args, **kwargs)
        self.fields['archive_time'].help_text = (
            "Input timezone is <b>UTC</b>"
        )
        if self.initial['archive_time']:
            # Force it to a UTC string so Django doesn't convert it
            # to a timezone-less string in the settings.TIME_ZONE timezone.
            self.initial['archive_time'] = (
                self.initial['archive_time'].strftime('%Y-%m-%d %H:%M:%S')
            )

    def clean_archive_time(self):
        value = self.cleaned_data['archive_time']
        # force it back to UTC
        if value:
            value = value.replace(tzinfo=utc)
        return value


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
            '<b class="char-counter">140</b> characters left. '
            '<span class="char-counter-warning"><b>Note!</b> Sometimes '
            'Twitter can count it as longer than it appears if you '
            'include a URL. '
            'It\'s usually best to leave a little room.</span>'
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

        if event.placeholder_img or event.picture:
            from airmozilla.main.templatetags.jinja_helpers import thumbnail
            if event.picture:
                pic = event.picture.file
            else:
                pic = event.placeholder_img
            thumb = thumbnail(pic, '160x90', crop='center')

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

        self.fields['send_date'].help_text = 'Timezone is UTC'


class ChannelForm(BaseModelForm):
    class Meta:
        model = Channel
        exclude = ('created', 'youtube_id')

    def __init__(self, *args, **kwargs):
        super(ChannelForm, self).__init__(*args, **kwargs)
        self.fields['parent'].required = False
        if kwargs.get('instance'):
            self.fields['parent'].choices = [
                (x, y) for (x, y)
                in self.fields['parent'].choices
                if x != kwargs['instance'].pk
            ]
        self.fields['cover_art'].help_text = (
            "The cover art for podcasts needs to be at least 1400x1400 "
            "pixels. Smaller versions that are needed will be derived "
            "from this same image."
        )

    def clean(self):
        cleaned_data = super(ChannelForm, self).clean()
        if 'always_show' in cleaned_data and 'never_show' in cleaned_data:
            # if one is true, the other one can't be
            if cleaned_data['always_show'] and cleaned_data['never_show']:
                raise forms.ValidationError(
                    "Can't both be on always and never shown"
                )
        return cleaned_data


class TemplateEditForm(BaseModelForm):
    class Meta:
        model = Template
        widgets = {
            'content': forms.Textarea(attrs={'rows': 20})
        }
        fields = (
            'name',
            'content',
            'default_popcorn_template',
            'default_archive_template',
        )


class TemplateMigrateForm(BaseForm):
    template = forms.ModelChoiceField(
        widget=forms.widgets.RadioSelect(),
        queryset=Template.objects.all()

    )

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.pop('instance')
        super(TemplateMigrateForm, self).__init__(*args, **kwargs)

        scheduled = defaultdict(int)
        removed = defaultdict(int)

        events = Event.objects.all()
        for each in events.values('template').annotate(Count('template')):
            scheduled[each['template']] = each['template__count']

        events = events.filter(status=Event.STATUS_REMOVED)
        for each in events.values('template').annotate(Count('template')):
            removed[each['template']] = each['template__count']

        choices = [('', '---------')]
        other_templates = Template.objects.exclude(id=self.instance.id)
        for template in other_templates.order_by('name'):
            choices.append((
                template.id,
                '{0} ({1} events, {2} removed)'.format(
                    template.name,
                    scheduled[template.id],
                    removed[template.id],
                )
            ))
        self.fields['template'].choices = choices


class RecruitmentMessageEditForm(BaseModelForm):
    class Meta:
        model = RecruitmentMessage
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3})
        }
        exclude = ('modified_user', 'created')


class EventChapterEditForm(BaseModelForm):
    timestamp = forms.CharField(widget=forms.widgets.TextInput(
        attrs={
            'placeholder': 'For example: 22m0s'
        }
    ))

    class Meta:
        model = Chapter
        widgets = {
            'text': forms.widgets.TextInput()
        }
        exclude = ('user', 'created', 'event')

    def __init__(self, *args, **kwargs):
        self.max_timestamp = None
        if kwargs.get('instance'):
            self.max_timestamp = kwargs['instance'].event.duration
            if kwargs['instance'].timestamp:
                kwargs['instance'].timestamp = show_duration_compact(
                    kwargs['instance'].timestamp
                )
        super(EventChapterEditForm, self).__init__(*args, **kwargs)

    def clean_timestamp(self):
        value = self.cleaned_data['timestamp'].strip().replace(' ', '')
        hours = re.findall('(\d{1,2})h', value)
        minutes = re.findall('(\d{1,2})m', value)
        seconds = re.findall('(\d{1,2})s', value)
        if seconds:
            seconds = int(seconds[0])
        else:
            seconds = 0
        if minutes:
            minutes = int(minutes[0])
        else:
            minutes = 0
        if hours:
            hours = int(hours[0])
        else:
            hours = 0
        total = seconds + minutes * 60 + hours * 60 * 60
        if not total:
            raise forms.ValidationError('Must be greater than zero')
        if self.max_timestamp:
            if total >= self.max_timestamp:
                raise forms.ValidationError('Longer than video duration')
        return total


class SurveyEditForm(BaseModelForm):
    class Meta:
        model = Survey
        exclude = ('created', 'modified')

    def __init__(self, *args, **kwargs):
        super(SurveyEditForm, self).__init__(*args, **kwargs)
        self.fields['active'].validators.append(self.validate_active)
        self.fields['events'].required = False
        self.fields['events'].queryset = (
            self.fields['events'].queryset.order_by('title')
        )

    def validate_active(self, value):
        if value and not self.instance.question_set.count():
            raise forms.ValidationError(
                "Survey must have at least one question in order to be active"
            )


class SurveyNewForm(BaseModelForm):
    class Meta:
        model = Survey
        fields = ('name', )


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
        fields = ('name', 'timezone', 'is_active', 'regions')


class LocationDefaultEnvironmentForm(BaseModelForm):

    class Meta:
        model = LocationDefaultEnvironment
        fields = ('privacy', 'template', 'template_environment')
        widgets = {
            'template_environment': forms.widgets.Textarea()
        }


class RegionEditForm(BaseModelForm):

    class Meta:
        model = Region
        fields = ('name', 'is_active')


class TopicEditForm(BaseModelForm):

    class Meta:
        model = Topic
        fields = ('topic', 'sort_order', 'groups', 'is_active')

    def __init__(self, *args, **kwargs):
        super(TopicEditForm, self).__init__(*args, **kwargs)
        self.fields['topic'].widget = forms.widgets.TextInput(attrs={
            'placeholder': 'for example Partners for Firefox OS'
        })


class ApprovalForm(BaseModelForm):
    class Meta:
        model = Approval
        fields = ('comment',)
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3})
        }


class HeadersField(forms.CharField):
    widget = forms.widgets.Textarea

    def __init__(self, *args, **kwargs):
        super(HeadersField, self).__init__(*args, **kwargs)
        self.help_text = self.help_text or mark_safe(
            "For example <code>Content-Type: text/xml</code>"
        )

    def to_python(self, value):
        if not value:
            return {}
        headers = {}
        for line in [x.strip() for x in value.splitlines() if x.strip()]:
            try:
                key, value = line.split(':', 1)
            except ValueError:
                raise forms.ValidationError(line)
            headers[key.strip()] = value.strip()
        return headers

    def prepare_value(self, value):
        if isinstance(value, basestring):
            # already prepared
            return value
        elif value is None:
            return ''
        out = []
        for key in sorted(value):
            out.append('%s: %s' % (key, value[key]))
        return '\n'.join(out)

    def widget_attrs(self, widget):
        attrs = super(HeadersField, self).widget_attrs(widget)
        if 'rows' not in attrs:
            attrs['rows'] = 3
        return attrs


class StaticPageEditForm(BaseModelForm):
    headers = HeadersField(required=False)

    class Meta:
        model = StaticPage
        fields = (
            'url',
            'title',
            'content',
            'privacy',
            'template_name',
            'allow_querystring_variables',
            'headers',
        )

    def __init__(self, *args, **kwargs):
        super(StaticPageEditForm, self).__init__(*args, **kwargs)
        self.fields['url'].label = 'URL'
        self.fields['template_name'].label = 'Template'
        choices = (
            ('', 'Default'),
            ('staticpages/nosidebar.html', 'Default (but no sidebar)'),
            ('staticpages/blank.html', 'Blank (no template wrapping)'),
        )
        self.fields['template_name'].widget = forms.widgets.Select(
            choices=choices
        )

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

    def clean(self):
        cleaned_data = super(StaticPageEditForm, self).clean()
        if 'url' in cleaned_data and 'privacy' in cleaned_data:
            if cleaned_data['url'].startswith('sidebar_'):
                if cleaned_data['privacy'] != Event.PRIVACY_PUBLIC:
                    raise forms.ValidationError(
                        "If a sidebar the privacy must be public"
                    )
        return cleaned_data


class VidlyURLForm(forms.Form):
    url = forms.CharField(
        required=True,
        label='URL',
        widget=forms.widgets.TextInput(attrs={
            'placeholder': 'E.g. http://videos.mozilla.org/.../file.flv',
            'class': 'input-xxlarge',
        })
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
        fields = ('name',)

    def clean_name(self):
        value = self.cleaned_data['name']
        other_tags = Tag.objects.filter(name__iexact=value)
        if self.instance:
            other_tags = other_tags.exclude(id=self.instance.id)
        if other_tags.exists():
            raise forms.ValidationError(
                'Used by another tag. Consider merging.'
            )
        return value


class TagMergeRepeatedForm(BaseForm):

    keep = forms.ChoiceField(
        label='Name to keep',
        widget=forms.widgets.RadioSelect()
    )

    def __init__(self, this_tag, *args, **kwargs):
        super(TagMergeRepeatedForm, self).__init__(*args, **kwargs)

        def describe_tag(tag):
            count = Event.objects.filter(tags=tag).count()
            if count == 1:
                tmpl = '%s (%d time)'
            else:
                tmpl = '%s (%d times)'
            return tmpl % (tag.name, count)

        self.fields['keep'].choices = [
            (x.id, describe_tag(x))
            for x in Tag.objects.filter(name__iexact=this_tag.name)
        ]


class TagMergeForm(BaseForm):

    name = forms.CharField()

    def __init__(self, this_tag, *args, **kwargs):
        super(TagMergeForm, self).__init__(*args, **kwargs)
        self.this_tag = this_tag

    def clean_name(self):
        value = self.cleaned_data['name']
        other_tags = (
            Tag.objects
            .filter(name__iexact=value)
            .exclude(id=self.this_tag.id)
        )
        if not other_tags.exists():
            raise forms.ValidationError('Not found')
        return value


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
        permission_required = kwargs.pop('permission_required')
        super(EventAssignmentForm, self).__init__(*args, **kwargs)
        users = (
            User.objects
            .extra(select={
                'email_lower': 'LOWER(email)'
            })
            .filter(is_active=True, is_staff=True)
            .filter(groups__permissions=permission_required)
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
            Location.objects.filter(is_active=True)
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


class QuestionForm(BaseModelForm):

    class Meta:
        model = Question
        fields = ('question',)


class EventSurveyForm(BaseForm):

    survey = forms.ChoiceField(
        widget=forms.widgets.RadioSelect()
    )

    def __init__(self, *args, **kwargs):
        super(EventSurveyForm, self).__init__(*args, **kwargs)

        def describe_survey(survey):
            output = survey.name
            if not survey.active:
                output += ' (not active)'
            count_questions = Question.objects.filter(survey=survey).count()
            if count_questions == 1:
                output += ' (1 question)'
            else:
                output += ' (%d questions)' % count_questions
            return output

        self.fields['survey'].choices = [
            ('0', 'none')
        ] + [
            (x.id, describe_survey(x)) for x in Survey.objects.all()
        ]


class PictureForm(BaseModelForm):

    class Meta:
        model = Picture
        fields = ('file', 'notes', 'default_placeholder', 'is_active')
        help_texts = {
            'is_active': (
                "Only active pictures is a choice when users pick picture."
            ),
        }


class AutocompeterUpdateForm(BaseForm):
    verbose = forms.BooleanField(required=False)
    max_ = forms.IntegerField(required=False)
    all = forms.BooleanField(required=False)
    flush_first = forms.BooleanField(required=False)
    since = forms.IntegerField(
        required=False,
        help_text="Minutes since last modified"
    )

    def clean_since(self):
        value = self.cleaned_data['since']
        if value:
            print "Minutes", int(value)
            value = datetime.timedelta(minutes=int(value))
        return value


class ISODateTimeField(forms.DateTimeField):

    def strptime(self, value, __):
        return dateutil.parser.parse(value)


class EventsDataForm(BaseForm):

    since = ISODateTimeField(required=False)


class TriggerErrorForm(BaseForm):

    message = forms.CharField()
    capture_with_raven = forms.BooleanField(required=False)


class ReindexRelatedContentForm(BaseForm):

    all = forms.BooleanField(required=False)
    since = forms.IntegerField(
        required=False,
        help_text='minutes',
        widget=forms.widgets.NumberInput(attrs={
            'style': 'width: 200px',
        })
    )
    delete_and_recreate = forms.BooleanField(required=False)


class RelatedContentTestingForm(BaseForm):

    event = forms.CharField(
        help_text="Title, slug or ID"
    )
    use_title = forms.BooleanField(required=False)
    boost_title = forms.FloatField()
    use_tags = forms.BooleanField(required=False)
    boost_tags = forms.FloatField()
    size = forms.IntegerField()

    def clean_event(self):
        event = self.cleaned_data['event'].strip()
        try:
            if not event.isdigit():
                raise Event.DoesNotExist
            return Event.objects.get(id=event)

        except Event.DoesNotExist:
            try:
                return Event.objects.get(slug__iexact=event)
            except Event.DoesNotExist:
                try:
                    return Event.objects.get(title__iexact=event)
                except Event.DoesNotExist:
                    raise forms.ValidationError("Event can't be found")
                except Event.MultipleObjectsReturned:
                    raise forms.ValidationError(
                        'Event title ambiguous. Use slug or ID.'
                    )

    def clean(self):
        cleaned_data = super(RelatedContentTestingForm, self).clean()
        if 'use_title' in cleaned_data and 'use_tags' in cleaned_data:
            if not (cleaned_data['use_title'] or cleaned_data['use_tags']):
                raise forms.ValidationError(
                    'One of Use title OR Use tags must be chosen'
                )
        return cleaned_data


class EventDurationForm(BaseModelForm):

    class Meta:
        model = Event
        fields = ('duration',)

    def __init__(self, *args, **kwargs):
        super(EventDurationForm, self).__init__(*args, **kwargs)
        self.fields['duration'].required = False
        self.fields['duration'].help_text = (
            "Note! If you remove this value (make it blank), it will be "
            "unset and automatically be re-evaluated."
        )


class EmailSendingForm(BaseForm):

    to = forms.CharField(
        help_text='Semi colon separated list of emails'
    )
    subject = forms.CharField()
    html_body = forms.CharField(
        label='HTML Body',
        widget=forms.widgets.Textarea()
    )

    def clean_to(self):
        value = self.cleaned_data['to']
        value = [x.strip() for x in value.split(';') if x.strip()]
        if not value:
            raise forms.ValidationError('Email list of emails')
        return value
