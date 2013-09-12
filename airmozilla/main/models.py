import datetime
import hashlib
import os
import unicodedata

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.db import models
from django.db.models import Q
from django.dispatch import receiver
from django.utils.timezone import utc

from airmozilla.base.utils import unique_slugify
from airmozilla.main.fields import EnvironmentField

import pytz
from sorl.thumbnail import ImageField


def _get_now():
    return datetime.datetime.utcnow().replace(tzinfo=utc)


def _get_live_time():
    return (_get_now() +
            datetime.timedelta(minutes=settings.LIVE_MARGIN))


class UserProfile(models.Model):
    user = models.ForeignKey(User)
    contributor = models.BooleanField(default=False)


@receiver(models.signals.post_save, sender=UserProfile)
def user_profile_clear_cache(sender, instance, **kwargs):
    cache.delete('is-contributor-%s' % instance.user.pk)


def get_profile_safely(user, create_if_necessary=False):
    try:
        return user.get_profile()
    except UserProfile.DoesNotExist:
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


class Participant(models.Model):
    """ Participants - speakers at events. """
    name = models.CharField(max_length=50)
    slug = models.SlugField(blank=True, max_length=65, unique=True,
                            db_index=True)
    photo = ImageField(upload_to=_upload_path('participant-photo'), blank=True)
    email = models.EmailField(blank=True)
    department = models.CharField(max_length=50, blank=True)
    team = models.CharField(max_length=50, blank=True)
    irc = models.CharField(max_length=50, blank=True)
    topic_url = models.URLField(blank=True)
    blog_url = models.URLField(blank=True)
    twitter = models.CharField(max_length=50, blank=True)
    ROLE_EVENT_COORDINATOR = 'event-coordinator'
    ROLE_PRINCIPAL_PRESENTER = 'principal-presenter'
    ROLE_PRESENTER = 'presenter'
    ROLE_CHOICES = (
        (ROLE_EVENT_COORDINATOR, 'Event Coordinator'),
        (ROLE_PRINCIPAL_PRESENTER, 'Principal Presenter'),
        (ROLE_PRESENTER, 'Presenter'),
    )
    role = models.CharField(max_length=25, choices=ROLE_CHOICES)
    CLEARED_YES = 'yes'
    CLEARED_NO = 'no'
    CLEARED_FINAL_CUT = 'final-cut'
    CLEARED_SUGGESTED = 'suggested'
    CLEARED_CHOICES = (
        (CLEARED_YES, 'Yes'),
        (CLEARED_NO, 'No'),
        (CLEARED_FINAL_CUT, 'Final Cut'),
        (CLEARED_SUGGESTED, 'Suggested'),
    )
    cleared = models.CharField(max_length=15,
                               choices=CLEARED_CHOICES, default=CLEARED_NO,
                               db_index=True)
    clear_token = models.CharField(max_length=36, blank=True)
    creator = models.ForeignKey(User, related_name='participant_creator',
                                blank=True, null=True,
                                on_delete=models.SET_NULL)

    class Meta:
        permissions = (
            ('change_participant_others', 'Can edit participants created by'
                                          ' other users'),
        )

    def is_clear(self):
        return self.cleared == Participant.CLEARED_YES

    def __unicode__(self):
        return self.name


class Category(models.Model):
    """ Categories globally divide events - one category per event. """
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name


class Channel(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100, unique=True,
                            db_index=True)
    image = ImageField(upload_to=_upload_path('channels'), blank=True)
    image_is_banner = models.BooleanField(default=False)
    description = models.TextField()
    created = models.DateTimeField(default=_get_now)

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name


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
        ' <code>request</code>, <code>datetime</code>, and <code>event</code>'
        ' objects, and the <code>md5</code> function. '
        ' Additionally we have <code>vidly_tokenize(tag, seconds)</code> and'
        ' <code>edgecast_tokenize([seconds], **kwargs)</code>.<br>'
        ' Warning! Changes affect'
        ' all events associated with this template.')

    def __unicode__(self):
        return self.name


class Location(models.Model):
    """Venue/location of a video/stream/presentation/etc."""
    name = models.CharField(max_length=300)
    timezone = models.CharField(max_length=250)

    def __unicode__(self):
        return self.name


class EventManager(models.Manager):
    def initiated(self):
        return (self.get_query_set().filter(Q(status=Event.STATUS_INITIATED) |
                                            Q(approval__approved=False) |
                                            Q(approval__processed=False))
                    .distinct())

    def approved(self):
        return (self.get_query_set().exclude(approval__approved=False)
                    .exclude(approval__processed=False)
                    .filter(status=Event.STATUS_SCHEDULED))

    def upcoming(self):
        return self.approved().filter(
            archive_time=None,
            start_time__gt=_get_live_time()
        )

    def live(self):
        return self.approved().filter(
            archive_time=None,
            start_time__lt=_get_live_time()
        )

    def archiving(self):
        return self.approved().filter(
            archive_time__gt=_get_now(),
            start_time__lt=_get_live_time()
        )

    def archived(self):
        _now = _get_now()
        return self.approved().filter(
            archive_time__lt=_now,
            start_time__lt=_now
        )

    def archived_and_removed(self):
        _now = _get_now()
        return self.get_query_set().filter(
            (Q(archive_time__lt=_now, start_time__lt=_now)
             & ~Q(approval__approved=False)
             & ~Q(approval__processed=False)
             & Q(status=Event.STATUS_SCHEDULED))
            | Q(status=Event.STATUS_REMOVED)
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
    placeholder_img = ImageField(upload_to=_upload_path('event-placeholder'))
    description = models.TextField()
    short_description = models.TextField(
        blank=True,
        help_text='If not provided, this will be filled in by the first '
        'words of the full description.'
    )
    start_time = models.DateTimeField(db_index=True)
    archive_time = models.DateTimeField(blank=True, null=True, db_index=True)
    participants = models.ManyToManyField(
        Participant,
        help_text='Speakers or presenters for this event.'
    )
    location = models.ForeignKey(Location, blank=True, null=True,
                                 on_delete=models.SET_NULL)
    category = models.ForeignKey(Category, blank=True, null=True,
                                 on_delete=models.SET_NULL)
    tags = models.ManyToManyField(Tag, blank=True)
    channels = models.ManyToManyField(Channel)
    call_info = models.TextField(blank=True)
    additional_links = models.TextField(blank=True)
    remote_presenters = models.TextField(blank=True, null=True)

    PRIVACY_PUBLIC = 'public'
    PRIVACY_COMPANY = 'company'
    PRIVACY_CONTRIBUTORS = 'contributors'
    PRIVACY_CHOICES = (
        (PRIVACY_PUBLIC, 'Public'),
        (PRIVACY_CONTRIBUTORS, 'Employees and contributors only'),
        (PRIVACY_COMPANY, 'Employees only'),
    )
    privacy = models.CharField(max_length=40, choices=PRIVACY_CHOICES,
                               default=PRIVACY_PUBLIC, db_index=True)
    featured = models.BooleanField(default=False, db_index=True)
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


class SuggestedEvent(models.Model):
    user = models.ForeignKey(User)
    title = models.CharField(max_length=200)
    slug = models.SlugField(blank=True, max_length=215, unique=True,
                            db_index=True)
    placeholder_img = ImageField(upload_to=_upload_path('event-placeholder'))
    description = models.TextField()
    short_description = models.TextField(
        blank=True,
        help_text='If not provided, this will be filled in by the first '
        'words of the full description.'
    )
    start_time = models.DateTimeField(db_index=True, blank=True, null=True)
    location = models.ForeignKey(Location, blank=True, null=True,
                                 on_delete=models.SET_NULL)
    category = models.ForeignKey(Category, blank=True, null=True,
                                 on_delete=models.SET_NULL)
    tags = models.ManyToManyField(Tag, blank=True)
    channels = models.ManyToManyField(Channel)
    call_info = models.TextField(blank=True)
    additional_links = models.TextField(blank=True)
    remote_presenters = models.TextField(blank=True, null=True)

    privacy = models.CharField(max_length=40, choices=Event.PRIVACY_CHOICES,
                               default=Event.PRIVACY_PUBLIC)
    featured = models.BooleanField(default=False)
    created = models.DateTimeField(default=_get_now)
    modified = models.DateTimeField(auto_now=True)

    participants = models.ManyToManyField(
        Participant,
        help_text='Speakers or presenters for this event.'
    )

    submitted = models.DateTimeField(blank=True, null=True)
    accepted = models.ForeignKey(Event, blank=True, null=True)
    review_comments = models.TextField(blank=True, null=True)

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
        instance.slug = unique_slugify(instance.title, [Event, EventOldSlug],
                                       instance.start_time.strftime('%Y%m%d'))
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


@receiver(models.signals.pre_save, sender=Participant)
def participant_update_slug(sender, instance, raw, *args, **kwargs):
    if not raw and not instance.slug:
        instance.slug = unique_slugify(instance.name, [Participant])


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
