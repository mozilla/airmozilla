from airmozilla.manage.videoinfo import fetch_screencapture


def create_timestamp_pictures(event, timestamps, verbose=False):
    fetch_screencapture(
        event,
        timestamps=timestamps,
        import_=True,
        import_immediately=True,
        verbose=verbose,
    )
