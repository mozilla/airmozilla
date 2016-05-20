import os
from functools import partial

from django.db.models import Q
from django.core.files import File

from airmozilla.manage.videoinfo import fetch_screencapture
from airmozilla.main.models import Chapter


def create_missing_chapterimages(verbose=False, max_=10):
    chapters = Chapter.objects.filter(
        event__duration__isnull=False,
    ).filter(
        # Chapters altered by migration will have NULL on image.
        # Those created without an image passed will automatically
        # be an empty string.
        Q(image__isnull=True) | Q(image='')
    )
    # When we know more about how to deal with YouTube content, we can
    # lift this filtering.
    chapters = chapters.filter(event__template__name__icontains='vid.ly')

    for chapter in chapters.order_by('?')[:max_]:
        if verbose:  # pragma: no cover
            print repr(chapter)
        create_chapterimages(chapter, verbose=verbose)


def create_chapterimages(chapter, verbose=False):

    def saved_file(chapter, filepath):
        with open(filepath, 'rb') as fp:
            opened = File(fp)
            chapter.image.save(os.path.basename(filepath), opened, save=True)
            return True

    fetch_screencapture(
        chapter.event,
        timestamps=[chapter.timestamp],
        import_=True,
        import_immediately=True,
        verbose=verbose,
        callback=partial(saved_file, chapter)
    )
