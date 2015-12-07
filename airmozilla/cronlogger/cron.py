import cronjobs

from .decorators import capture
from . import cleanup


@cronjobs.register
@capture
def purge_old_cronlogs():
    cleanup.purge_old(verbose=True)
