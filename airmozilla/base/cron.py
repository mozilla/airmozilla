import cronjobs

from airmozilla.cronlogger.decorators import capture
from . import mozillians


@cronjobs.register
@capture
def keep_all_mozillians_group_cache_hot():  # pragma: no cover
    print len(mozillians.get_all_groups_cached()), "groups"
