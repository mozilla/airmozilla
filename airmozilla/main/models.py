import datetime
import hashlib
import os
import unicodedata

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.db import models
from django.dispatch import receiver
from django.utils import timezone

from airmozilla.base.utils import unique_slugify
from airmozilla.main.fields import EnvironmentField
from airmozilla.manage.utils import filename_to_notes

import pytz
from sorl.thumbnail import ImageField


def _get_now():
    return timezone.now()


def _get_live_time():
    return (_get_now() +
            datetime.timedelta(minutes=settings.LIVE_MARGIN))


class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='profile')
    contributor = models.BooleanField(default=False)


@receiver(models.signals.post_delete, sender=UserProfile)
@receiver(models.signals.post_delete, sender=User)
@receiver(models.signals.post_save, sender=UserProfile)
@receiver(models.signals.post_save, sender=User)
def user_profile_clear_cache(sender, instance, **kwargs):
    if instance.__class__ is User:
        pk = instance.pk
    elif instance.__class__ is UserProfile:
        pk = instance.user.pk
    else:
        raise NotImplementedError
    cache.delete('is-contributor-%s' % pk)


def get_profile_safely(user, create_if_necessary=False):
    try:
        return user.profile
    except (UserProfile.DoesNotExist, AttributeError):
        # AttributeErrors happen if user is instance of AnonymousUser
        if create_if_necessary:
            return UserProfile.objects.create(user=user)


def _upload_path(tag):
    def _upload_path_tagged(instance, filename):
        if isinstance(filename, unicode):
            filename = (
                unicodedata
                .normalize('NFD', filename)
                .encode('ascii', 'ignore')
            )
        now = datetime.datetime.now()
        path = os.path.join(now.strftime('%Y'), now.strftime('%m'),
                            now.strftime('%d'))
        hashed_filename = (hashlib.md5(filename +
                           str(now.microsecond)).hexdigest())
        __, extension = os.path.splitext(filename)
        return os.path.join(tag, path, hashed_filename + extension)
    return _upload_path_tagged


class Channel(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100, unique=True,
                            db_index=True)
    image = ImageField(upload_to=_upload_path('channels'), blank=True)
    image_is_banner = models.BooleanField(default=False)
    parent = models.ForeignKey('self', name='parent', null=True)
    description = models.TextField()
    created = models.DateTimeField(default=_get_now)
    reverse_order = models.BooleanField(default=False)
    exclude_from_trending = models.BooleanField(default=False)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name

    def get_children(self):
        return Channel.objects.filter(parent=self)


class Tag(models.Model):
    """ Tags are flexible; events can have multiple tags. """
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return self.name


class Template(models.Model):
    """Provides the HTML embed codes, links, etc. for each different type of
       video or stream."""
    name = models.CharField(max_length=100)
    content = models.TextField(
        help_text='The HTML framework for this template.  Use'
        ' <code>{{ any_variable_name }}</code> for per-event'
        ' tags. Other Jinja2 constructs are available, along with the related'
        ' <code>request</code>, <code>datetime</code>, <code>event</code> '
        ' objects, <code>popcorn_url</code> and the <code>md5</code> function.'
        ' You can also reference <code>autoplay</code> and it\'s always safe.'
        ' Additionally we have <code>vidly_tokenize(tag, seconds)</code> and'
        ' <code>edgecast_tokenize([seconds], **kwargs)</code>.<br>'
        ' Warning! Changes affect'
        ' all events associated with this template.'
    )
    default_popcorn_template = models.BooleanField(
        default=False,
        help_text='If you have more than one templates for Popcorn videos '
                  'this dictates which one is the default one.'
    )
    default_archive_template = models.BooleanField(
        default=False,
        help_text='When you archive an event, it needs to preselect which '
                  'template it should use. This selects the best default.'
    )

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name


class Region(models.Model):
    """Region of a video/stream/presentation/etc."""
    name = models.CharField(max_length=300)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name


class Location(models.Model):
    """Venue/location of a video/stream/presentation/etc."""
    name = models.CharField(max_length=300)
    timezone = models.CharField(max_length=250)
    is_active = models.BooleanField(default=True)
    regions = models.ManyToManyField(Region, blank=True)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name


class RecruitmentMessage(models.Model):
    text = models.CharField(max_length=250)
    url = models.URLField()
    active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    modified_user = models.ForeignKey(User, null=True,
                                      on_delete=models.SET_NULL)
    created = models.DateTimeField(default=_get_now)
    modified = models.DateTimeField(auto_now=True, default=_get_now)

    class Meta:
        ordering = ['text']

    def __unicode__(self):
        return self.text


class ApprovableQuerySet(models.query.QuerySet):

    def approved(self):
        return (
            self._clone()
            .exclude(approval__approved=False)
            .exclude(approval__processed=False)
        )


class EventManager(models.Manager):

    def get_queryset(self):
        return ApprovableQuerySet(self.model, using=self._db)

    def scheduled(self):
        return self.get_query_set().filter(status=Event.STATUS_SCHEDULED)

    def approved(self):
        return (
            self.scheduled()
            .exclude(approval__approved=False)
            .exclude(approval__processed=False)
        )

    def upcoming(self):
        return self.scheduled().filter(
            archive_time=None,
            start_time__gt=_get_live_time()
        )

    def live(self):
        return self.scheduled().filter(
            archive_time=None,
            start_time__lt=_get_live_time()
        )

    def archived(self):
        _now = _get_now()
        return self.scheduled().filter(
            archive_time__lt=_now,
            start_time__lt=_now
        )


class Event(models.Model):
    """ Events - all the essential data and metadata for publishing. """
    title = models.CharField(max_length=200)
    slug = models.SlugField(blank=True, max_length=215, unique=True,
                            db_index=True)
    template = models.ForeignKey(Template, blank=True, null=True,
                                 on_delete=models.SET_NULL)
    template_environment = EnvironmentField(
        blank=True,
        help_text='Specify the template variables in the format'
        '<code>variable1=value</code>, one per line.'
    )
    STATUS_INITIATED = 'initiated'
    STATUS_SCHEDULED = 'scheduled'
    STATUS_PENDING = 'pending'
    STATUS_REMOVED = 'removed'
    STATUS_CHOICES = (
        (STATUS_INITIATED, 'Initiated'),
        (STATUS_SCHEDULED, 'Scheduled'),
        (STATUS_PENDING, 'Pending'),
        (STATUS_REMOVED, 'Removed')
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default=STATUS_INITIATED, db_index=True)
    placeholder_img = ImageField(
        upload_to=_upload_path('event-placeholder'),
        blank=True,
        null=True,
    )
    picture = models.ForeignKey(
        'Picture',
        blank=True,
        null=True,
        related_name='event_picture',
        on_delete=models.SET_NULL
    )
    upload = models.ForeignKey(
        'uploads.Upload',
        null=True,
        related_name='event_upload',
        on_delete=models.SET_NULL
    )
    description = models.TextField()
    short_description = models.TextField(
        blank=True,
        help_text='If not provided, this will be filled in by the first '
        'words of the full description.'
    )
    start_time = models.DateTimeField(db_index=True)
    archive_time = models.DateTimeField(blank=True, null=True, db_index=True)
    location = models.ForeignKey(Location, blank=True, null=True,
                                 on_delete=models.SET_NULL)
    tags = models.ManyToManyField(Tag, blank=True)
    channels = models.ManyToManyField(Channel)
    call_info = models.TextField(blank=True)
    additional_links = models.TextField(blank=True)
    remote_presenters = models.TextField(blank=True, null=True)

    popcorn_url = models.URLField(null=True, blank=True)

    PRIVACY_PUBLIC = 'public'
    PRIVACY_COMPANY = 'company'
    PRIVACY_CONTRIBUTORS = 'contributors'
    PRIVACY_CHOICES = (
        (PRIVACY_PUBLIC, 'Public'),
        (PRIVACY_CONTRIBUTORS, 'Contributors'),
        (PRIVACY_COMPANY, 'Staff'),
    )
    privacy = models.CharField(max_length=40, choices=PRIVACY_CHOICES,
                               default=PRIVACY_PUBLIC, db_index=True)
    featured = models.BooleanField(default=False, db_index=True)
    pin = models.CharField(max_length=20, null=True, blank=True)
    transcript = models.TextField(null=True)
    recruitmentmessage = models.ForeignKey(RecruitmentMessage, null=True,
                                           on_delete=models.SET_NULL)
    duration = models.PositiveIntegerField(null=True)  # seconds
    mozillian = models.CharField(max_length=200, null=True)
    creator = models.ForeignKey(User, related_name='creator', blank=True,
                                null=True, on_delete=models.SET_NULL)
    created = models.DateTimeField(auto_now_add=True)
    modified_user = models.ForeignKey(User, related_name='modified_user',
                                      blank=True, null=True,
                                      on_delete=models.SET_NULL)
    modified = models.DateTimeField(auto_now=True)
    objects = EventManager()

    class Meta:
        permissions = (
            ('change_event_others', 'Can edit events created by other users'),
            ('add_event_scheduled', 'Can create events with scheduled status')
        )

    def __unicode__(self):
        return self.title

    def is_upcoming(self):
        return (self.archive_time is None and
                self.start_time > _get_live_time())

    def is_removed(self):
        return self.status == self.STATUS_REMOVED

    def is_public(self):
        return self.privacy == self.PRIVACY_PUBLIC

    def is_scheduled(self):
        return self.status == self.STATUS_SCHEDULED

    def is_pending(self):
        return self.status == self.STATUS_PENDING

    def is_live(self):
        return (
            not self.archive_time and
            self.start_time and
            self.start_time < _get_live_time()
        )

    def needs_approval(self):
        if self.is_scheduled():
            for approval in Approval.objects.filter(event=self):
                if approval.processed:
                    return False
                if not approval.approved:
                    return True
        return False

    def has_vidly_template(self):
        return self.template and 'Vid.ly' in self.template.name

    @property
    def location_time(self):
        assert self.location
        tz = pytz.timezone(self.location.timezone)
        return tz.normalize(self.start_time)


def most_recent_event():
    cache_key = 'most_recent_event'
    event = cache.get(cache_key)
    if event is None:
        for event in Event.objects.all().order_by('-modified')[:1]:
            cache.set(cache_key, event, 60 * 60)
    return event


@receiver(models.signals.post_save, sender=Event)
def reset_most_recent_event(sender, instance, *args, **kwargs):
    cache_key = 'most_recent_event'
    cache.delete(cache_key)


class EventRevisionManager(models.Manager):

    def create_from_event(self, event, user=None):
        revision = self.create(
            event=event,
            user=user,
            title=event.title,
            placeholder_img=event.placeholder_img,
            picture=event.picture,
            description=event.description,
            short_description=event.short_description,
            call_info=event.call_info,
            additional_links=event.additional_links,
            recruitmentmessage=event.recruitmentmessage,
        )
        for channel in event.channels.all():
            revision.channels.add(channel)
        for tag in event.tags.all():
            revision.tags.add(tag)
        return revision


class EventRevision(models.Model):
    event = models.ForeignKey(Event)
    user = models.ForeignKey(User, null=True)
    title = models.CharField(max_length=200)
    placeholder_img = ImageField(
        upload_to=_upload_path('event-placeholder'), blank=True, null=True)
    picture = models.ForeignKey('Picture', blank=True, null=True)
    description = models.TextField()
    short_description = models.TextField(
        blank=True,
        help_text='If not provided, this will be filled in by the first '
        'words of the full description.'
    )
    channels = models.ManyToManyField(Channel)
    tags = models.ManyToManyField(Tag, blank=True)
    call_info = models.TextField(blank=True)
    additional_links = models.TextField(blank=True)
    recruitmentmessage = models.ForeignKey(RecruitmentMessage, null=True,
                                           on_delete=models.SET_NULL)
    created = models.DateTimeField(default=_get_now)

    objects = EventRevisionManager()


class EventAssignment(models.Model):

    event = models.ForeignKey(Event, unique=True)
    locations = models.ManyToManyField(Location)
    users = models.ManyToManyField(User)
    created = models.DateTimeField(default=_get_now)
    modified = models.DateTimeField(auto_now=True)


class CuratedGroup(models.Model):

    event = models.ForeignKey(Event)
    name = models.CharField(max_length=200)
    url = models.URLField(null=True)
    created = models.DateTimeField(default=_get_now)


class SuggestedEvent(models.Model):
    user = models.ForeignKey(User)
    title = models.CharField(max_length=200)
    upcoming = models.BooleanField(default=True)
    slug = models.SlugField(blank=True, max_length=215, unique=True,
                            db_index=True)
    placeholder_img = ImageField(
        upload_to=_upload_path('event-placeholder'), blank=True, null=True)
    picture = models.ForeignKey('Picture', blank=True, null=True)
    upload = models.ForeignKey(
        'uploads.Upload',
        null=True,
        related_name='upload'
    )
    description = models.TextField()
    short_description = models.TextField(
        blank=True,
        help_text='If not provided, this will be filled in by the first '
        'words of the full description.'
    )
    start_time = models.DateTimeField(db_index=True, blank=True, null=True)
    location = models.ForeignKey(Location, blank=True, null=True,
                                 on_delete=models.SET_NULL)
    tags = models.ManyToManyField(Tag, blank=True)
    channels = models.ManyToManyField(Channel)
    call_info = models.TextField(blank=True)
    additional_links = models.TextField(blank=True)
    remote_presenters = models.TextField(blank=True, null=True)

    popcorn_url = models.URLField(null=True, blank=True)

    privacy = models.CharField(max_length=40, choices=Event.PRIVACY_CHOICES,
                               default=Event.PRIVACY_PUBLIC)
    featured = models.BooleanField(default=False)
    created = models.DateTimeField(default=_get_now)
    modified = models.DateTimeField(auto_now=True)

    first_submitted = models.DateTimeField(blank=True, null=True)
    submitted = models.DateTimeField(blank=True, null=True)
    accepted = models.ForeignKey(Event, blank=True, null=True)
    review_comments = models.TextField(blank=True, null=True)

    STATUS_CREATED = 'created'
    STATUS_SUBMITTED = 'submitted'
    STATUS_RESUBMITTED = 'resubmitted'
    STATUS_RETRACTED = 'retracted'
    STATUS_REJECTED = 'rejected'
    STATUS_ACCEPTED = 'accepted'
    STATUS_CHOICES = (
        (STATUS_CREATED, 'Created'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_RESUBMITTED, 'Resubmitted'),
        (STATUS_REJECTED, 'Bounced back'),
        (STATUS_RETRACTED, 'Retracted'),
        (STATUS_ACCEPTED, 'Accepted'),
    )
    status = models.CharField(
        max_length=40,
        choices=STATUS_CHOICES,
        default=STATUS_CREATED,
    )

    objects = EventManager()

    def __unicode__(self):
        return self.title

    @property
    def location_time(self):
        tz = pytz.timezone(self.location.timezone)
        return tz.normalize(self.start_time)


class SuggestedEventComment(models.Model):
    suggested_event = models.ForeignKey(SuggestedEvent, db_index=True)
    comment = models.TextField()
    user = models.ForeignKey(User, blank=True, null=True,
                             on_delete=models.SET_NULL)
    created = models.DateTimeField(default=_get_now)


class EventOldSlug(models.Model):
    """Used to permanently redirect old URLs to the new slug location."""
    event = models.ForeignKey(Event, db_index=True)
    slug = models.SlugField(max_length=215, unique=True, db_index=True)

    def __unicode__(self):
        return "%r -> %r" % (self.slug, self.event.slug)


class EventTweet(models.Model):
    """Used for prepareing a tweet and possibly sending it later."""
    event = models.ForeignKey(Event, db_index=True)
    text = models.CharField(max_length=140)
    include_placeholder = models.BooleanField(default=False)
    creator = models.ForeignKey(User, blank=True, null=True,
                                on_delete=models.SET_NULL)
    # when to send it
    send_date = models.DateTimeField(default=_get_now)
    # when it was sent
    sent_date = models.DateTimeField(blank=True, null=True)
    error = models.TextField(blank=True, null=True)
    tweet_id = models.CharField(max_length=20, blank=True, null=True)

    def __unicode__(self):
        return self.text

    def __repr__(self):
        return "<%s: %r>" % (self.__class__.__name__, self.text)


class Approval(models.Model):
    """Sign events with approvals from appropriate user groups to log and
       designate that an event can be published."""
    event = models.ForeignKey(Event, db_index=True)
    group = models.ForeignKey(Group, blank=True, null=True,
                              on_delete=models.SET_NULL, db_index=True)
    user = models.ForeignKey(User, blank=True, null=True,
                             on_delete=models.SET_NULL)
    approved = models.BooleanField(default=False, db_index=True)
    processed = models.BooleanField(default=False, db_index=True)
    processed_time = models.DateTimeField(auto_now=True)
    comment = models.TextField(blank=True)


class VidlySubmission(models.Model):
    event = models.ForeignKey(Event)
    url = models.URLField()
    submission_time = models.DateTimeField(default=_get_now)
    tag = models.CharField(max_length=100, null=True, blank=True)
    # only used for synchronization, no longer something you can set
    email = models.EmailField(blank=True, null=True)
    token_protection = models.BooleanField(default=False)
    hd = models.BooleanField(default=False)
    submission_error = models.TextField(blank=True, null=True)


@receiver(models.signals.post_save, sender=Event)
@receiver(models.signals.post_save, sender=Approval)
def event_clear_cache(sender, **kwargs):
    cache.delete('calendar')
    cache.delete('calendar_public')
    cache.delete('calendar_company')
    cache.delete('calendar_contributors')
    cache.delete('autocomplete:patterns')


@receiver(models.signals.pre_save, sender=Event)
def event_update_slug(sender, instance, raw, *args, **kwargs):
    if raw:
        return
    if not instance.slug:
        exclude = {}
        if instance.id:
            exclude = {'id': instance.id}
        instance.slug = unique_slugify(
            instance.title, [Event, EventOldSlug],
            instance.start_time.strftime('%Y%m%d'),
            exclude=exclude
        )
    try:
        old = Event.objects.get(id=instance.id)
        if instance.slug != old.slug:
            [x.delete() for x in EventOldSlug.objects.filter(slug=old.slug)]
            EventOldSlug.objects.create(slug=old.slug, event=instance)
    except Event.DoesNotExist:
        pass


@receiver(models.signals.pre_save, sender=Event)
def event_consistent_times(sender, instance, raw, *arg, **kwargs):
    # Fix an edge case with disappearing events.
    # Enforce consistent start_time and archive_time, that is,
    # archive_time must be after start_time and not before it, if defined.
    if raw:
        return
    if instance.archive_time and instance.start_time > instance.archive_time:
        instance.archive_time = None


class URLMatch(models.Model):
    name = models.CharField(max_length=200)
    string = models.CharField(
        max_length=200,
        help_text="This matcher can contain basic regular expression "
                  "characters like <code>*</code>, <code>^</code> (only as "
                  "first character) and "
                  "<code>$</code> (only as last character)."
    )
    use_count = models.IntegerField(default=0)
    modified = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.name


class URLTransform(models.Model):
    match = models.ForeignKey(URLMatch)
    find = models.CharField(max_length=200)
    replace_with = models.CharField(max_length=200)
    order = models.IntegerField(default=1)


class EventHitStats(models.Model):
    event = models.ForeignKey(Event, unique=True, db_index=True)
    total_hits = models.IntegerField()
    shortcode = models.CharField(max_length=100)
    modified = models.DateTimeField(default=_get_now)


@receiver(models.signals.pre_save, sender=EventHitStats)
def update_modified(sender, instance, raw, *args, **kwargs):
    if raw:
        return
    instance.modified = _get_now()


class EventLiveHits(models.Model):
    event = models.ForeignKey(Event, unique=True, db_index=True)
    total_hits = models.IntegerField(default=0)
    modified = models.DateTimeField(auto_now=True)


class LocationDefaultEnvironment(models.Model):
    location = models.ForeignKey(Location)
    privacy = models.CharField(max_length=40, choices=Event.PRIVACY_CHOICES,
                               default=Event.PRIVACY_PUBLIC)
    template = models.ForeignKey(Template)
    template_environment = EnvironmentField(
        help_text='Specify the template variables in the format'
        '<code>variable1=value</code>, one per line.'
    )

    class Meta:
        unique_together = ('location', 'privacy', 'template')


class Picture(models.Model):
    size = models.PositiveIntegerField()
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    file = models.ImageField(
        upload_to=_upload_path('pictures'),
        width_field='width',
        height_field='height'
    )
    event = models.ForeignKey(Event, null=True, related_name='picture_event')

    # suggested_event = models.ForeignKey(SuggestedEvent, null=True)
    default_placeholder = models.BooleanField(default=False)
    notes = models.CharField(max_length=100, blank=True)
    modified_user = models.ForeignKey(User, null=True,
                                      on_delete=models.SET_NULL)
    created = models.DateTimeField(default=_get_now)
    modified = models.DateTimeField(auto_now=True, default=_get_now)

    def __repr__(self):
        return "<%s: %r>" % (self.__class__.__name__, self.notes)


@receiver(models.signals.pre_save, sender=Picture)
def update_size(sender, instance, *args, **kwargs):
    instance.size = instance.file.size
    if not instance.notes:
        instance.notes = filename_to_notes(instance.file.name)
