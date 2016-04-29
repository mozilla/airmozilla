from django.db import models
from django.dispatch import receiver

from jsonfield import JSONField

from airmozilla.main.models import Event


class AmaraVideo(models.Model):
    event = models.ForeignKey(Event)
    video_url = models.URLField()
    video_id = models.CharField(max_length=100)
    transcript = JSONField(null=True)
    upload_info = JSONField(null=True)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def url(self):
        return 'https://www.amara.org/videos/%s/' % self.video_id


@receiver(models.signals.post_save, sender=AmaraVideo)
def copy_transcript_as_text(sender, instance, **kwargs):
    """upon saving, pull out the plain text from the AmaraVideo
    transcript and turn it into a blob of plain text and store
    it in the Event"""
    if not instance.transcript:
        return
    if not instance.transcript.get('subtitles'):
        return
    text = []
    for block in instance.transcript['subtitles']:
        text.append(block['text'])
    instance.event.transcript = '\n'.join(text)
    instance.event.save()
