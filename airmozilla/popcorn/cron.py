import cronjobs

from airmozilla.cronlogger.decorators import capture
from airmozilla.popcorn.renderer import render_all_videos


@cronjobs.register
@capture
def render_popcorn():
    render_all_videos(
         verbose=True
    )
