from django.db import models
from django.contrib.auth.models import User
from django.db.models import Max
from django.core.cache import cache
from django.dispatch import receiver

from jsonfield.fields import JSONField

from airmozilla.main.models import Event


class Survey(models.Model):
    name = models.CharField(max_length=250, null=True)
    events = models.ManyToManyField(Event)
    active = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)


@receiver(models.signals.m2m_changed, sender=Survey.events.through)
@receiver(models.signals.post_save, sender=Survey)
def invalidate_event_survey_cache_key(sender, instance, **kwargs):
    for event in instance.events.all():
        cache_key = 'event_survey_id_%s' % event.id
        cache.delete(cache_key)


def next_order(*args, **kwargs):
    try:
        current_max = (
            Question.objects.all()
            .aggregate(Max('order'))['order__max']
        ) or 0
    except:  # pragma: no cover
        # an ugly hack for the sake of South
        # necessary for the first migration creation
        current_max = 0
    return current_max + 1


class Question(models.Model):
    survey = models.ForeignKey(Survey)
    question = JSONField()
    order = models.IntegerField(default=next_order)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __repr__(self):  # pragma: no cover
        return '<%r %r>' % (self.__class__.__name__, self.question)


class Answer(models.Model):
    user = models.ForeignKey(User)
    question = models.ForeignKey(Question)
    answer = JSONField()
    modified = models.DateTimeField(auto_now=True)

    def __repr__(self):  # pragma: no cover
        return '<%r %r>' % (self.__class__.__name__, self.answer)
