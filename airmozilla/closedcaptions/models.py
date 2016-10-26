import hashlib

import pycaption

from django.contrib.auth.models import User
from django.db import models
from django.contrib.postgres.fields import ArrayField

from jsonfield import JSONField

from airmozilla.main.models import Event, upload_path_tagged
from airmozilla.base import rev


class JSONTranscriptWriter(pycaption.base.BaseWriter):

    def write(self, caption_set):
        lang = caption_set.get_languages()[0]
        captions = caption_set.get_captions(lang)
        subtitles = []

        for caption in captions:
            subtitles.append({
                'start': caption.start / 1000,
                'end': caption.end / 1000,
                'text': caption.get_text().replace('\n', ' ').strip(),
            })
        return {'subtitles': subtitles}


def _upload_path_closed_captions(instance, filename):
    return upload_path_tagged('closed_captions', instance, filename)


class ClosedCaptions(models.Model):
    event = models.ForeignKey(Event)
    file = models.FileField(upload_to=_upload_path_closed_captions)

    transcript = JSONField(null=True)
    submission_info = JSONField(null=True)
    file_info = JSONField(null=True)

    created_user = models.ForeignKey(
        User,
        related_name='created_user',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    @property
    def filename_hash(self):
        """this is useful so that we can generate public URLs that
        we can send to services like Vid.yl without needing
        authentication."""
        return hashlib.md5(self.file.name).hexdigest()[:12]

    def set_transcript_from_file(self):
        content = self.file.read()
        reader = pycaption.detect_format(content)
        converter = pycaption.CaptionConverter()
        converter.read(content, reader())
        self.transcript = converter.write(JSONTranscriptWriter())

    def get_plaintext_transcript(self):
        if not self.transcript:
            self.set_transcript_from_file()
        subtitles = self.transcript['subtitles']
        lines = []
        for item in subtitles:
            lines.append(item['text'])
        return '\n'.join(lines)


class ClosedCaptionsTranscript(models.Model):
    event = models.OneToOneField(Event)
    closedcaptions = models.ForeignKey(ClosedCaptions)


class RevInput(models.Model):
    url = models.URLField(max_length=500)
    content_type = models.CharField(max_length=100, null=True)
    filename = models.CharField(max_length=100, null=True)
    uri = models.CharField(max_length=200, null=True)
    created = models.DateTimeField(auto_now_add=True)


class RevOrder(models.Model):
    event = models.ForeignKey(Event)
    order_number = models.CharField(max_length=100, null=True)
    uri = models.CharField(max_length=200, null=True)
    input = models.ForeignKey(RevInput)
    output_file_formats = ArrayField(
        models.CharField(max_length=100)
    )
    status = models.CharField(max_length=100, null=True)
    cancelled = models.BooleanField(default=False)
    metadata = JSONField(null=True)
    created_user = models.ForeignKey(
        User,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def update_status(self, save=True):
        assert self.uri
        self.metadata = self.get_order()
        self.status = self.metadata.get('status')
        if save:
            self.save()

    def get_order(self):
        return rev.get_order(self.uri)
