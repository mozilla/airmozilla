import datetime
import hashlib
import os

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.db import models
from django.db.models import Q
from django.dispatch import receiver
from django.utils.timezone import utc

from airmozilla.base.utils import unique_slugify
from airmozilla.main.fields import EnvironmentField
from sorl.thumbnail import ImageField


def _upload_path(tag):
    def _upload_path_tagged(instance, filename):
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
    slug = models.SlugField(blank=True, max_length=65, unique=True)
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
    CLEARED_CHOICES = (
        (CLEARED_YES, 'Yes'),
        (CLEARED_NO, 'No'),
        (CLEARED_FINAL_CUT, 'Final Cut'),
    )
    cleared = models.CharField(max_length=15,
                               choices=CLEARED_CHOICES, default=CLEARED_NO)
    clear_token = models.CharField(max_length=36, blank=True)
    creator = models.ForeignKey(User, related_name='participant_creator', blank=True,
                                null=True, on_delete=models.SET_NULL)

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
        ' objects, and the <code>md5</code> function. Warning! Changes affect'
        ' all events associated with this template.')

    def __unicode__(self):
        return self.name


class Location(models.Model):
    """Venue/location of a video/stream/presentation/etc."""
    name = models.CharField(max_length=300)
    timezone = models.CharField(max_length=250)

    def __unicode__(self):
        return self.name


def _get_now():
    return datetime.datetime.utcnow().replace(tzinfo=utc)


def _get_live_time():
    return (_get_now() +
            datetime.timedelta(minutes=settings.LIVE_MARGIN))


class EventManager(models.Manager):
    def initiated(self):
        return (self.get_query_set().filter(Q(status=Event.STATUS_INITIATED) |
                                            Q(approval__approved=False) |
                                            Q(approval__processed=False))
                    .distinct())

    def approved(self, include_removed=False):
        query_set = self.get_query_set()
        if include_removed:
            query_set = query_set.filter(Q(status=Event.STATUS_SCHEDULED) |
                                         Q(status=Event.STATUS_REMOVED))
        else:
            query_set = query_set.filter(status=Event.STATUS_SCHEDULED)
        return (query_set.exclude(approval__approved=False)
                         .exclude(approval__processed=False))

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

    def archived(self, include_removed=False):
        return self.approved(include_removed).filter(
            archive_time__lt=_get_now(),
            start_time__lt=_get_now()
        )


class Event(models.Model):
    """ Events - all the essential data and metadata for publishing. """
    title = models.CharField(max_length=200)
    slug = models.SlugField(blank=True, max_length=215, unique=True)
    template = models.ForeignKey(Template, blank=True, null=True,
                                 on_delete=models.SET_NULL)
    template_environment = EnvironmentField(
        blank=True,
        help_text='Specify the template variables in the format'
        '<code>variable1=value</code>, one per line.'
    )
    STATUS_INITIATED = 'initiated'
    STATUS_SCHEDULED = 'scheduled'
    STATUS_REMOVED = 'removed'
    STATUS_CHOICES = (
        (STATUS_INITIATED, 'Initiated'),
        (STATUS_SCHEDULED, 'Scheduled'),
        (STATUS_REMOVED, 'Removed')
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default=STATUS_INITIATED)
    placeholder_img = ImageField(upload_to=_upload_path('event-placeholder'))
    description = models.TextField()
    short_description = models.TextField(
        blank=True,
        help_text='If not provided, this will be filled in by the first '
        'words of the full description.'
    )
    start_time = models.DateTimeField()
    archive_time = models.DateTimeField(blank=True, null=True)
    participants = models.ManyToManyField(
        Participant,
        help_text='Speakers or presenters for this event.'
    )
    location = models.ForeignKey(Location, blank=True, null=True,
                                 on_delete=models.SET_NULL)
    category = models.ForeignKey(Category, blank=True, null=True,
                                 on_delete=models.SET_NULL)
    tags = models.ManyToManyField(Tag, blank=True)
    call_info = models.TextField(blank=True)
    additional_links = models.TextField(blank=True)
    public = models.BooleanField(
        default=False,
        help_text='Available to everyone (else MoCo only.)'
    )
    featured = models.BooleanField(default=False)
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

    def is_upcoming(self):
        return (self.archive_time is None and
                self.start_time > _get_live_time())
    
    def is_removed(self):
        return self.status == self.STATUS_REMOVED


class EventOldSlug(models.Model):
    """Used to permanently redirect old URLs to the new slug location."""
    event = models.ForeignKey(Event)
    slug = models.SlugField(max_length=215, unique=True)


class Approval(models.Model):
    """Sign events with approvals from appropriate user groups to log and
       designate that an event can be published."""
    event = models.ForeignKey(Event)
    group = models.ForeignKey(Group, blank=True, null=True,
                              on_delete=models.SET_NULL)
    user = models.ForeignKey(User, blank=True, null=True,
                             on_delete=models.SET_NULL)
    approved = models.BooleanField(default=False)
    processed = models.BooleanField(default=False)
    processed_time = models.DateTimeField(auto_now=True)
    comment = models.TextField(blank=True)


@receiver(models.signals.post_save, sender=Event)
@receiver(models.signals.post_save, sender=Approval)
def event_clear_cache(sender, **kwargs):
    cache.delete('calendar_public')
    cache.delete('calendar_private')


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
            EventOldSlug.objects.create(slug=old.slug, event=instance)
    except Event.DoesNotExist:
        pass


@receiver(models.signals.pre_save, sender=Participant)
def participant_update_slug(sender, instance, raw, *args, **kwargs):
    if not raw and not instance.slug:
        instance.slug = unique_slugify(instance.name, [Participant])
