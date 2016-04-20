import cronjobs

from airmozilla.cronlogger.decorators import capture
from . import images


@cronjobs.register
@capture
def create_chapterimages():
    images.create_missing_chapterimages(verbose=True, max_=5)
