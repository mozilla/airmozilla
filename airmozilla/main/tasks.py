from celery import shared_task

from airmozilla.main.models import Chapter
from airmozilla.chapters import images


@shared_task
def create_chapterimages(chapter_id):
    chapter = Chapter.objects.get(id=chapter_id)
    images.create_chapterimages(chapter, verbose=True)
