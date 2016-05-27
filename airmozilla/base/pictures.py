from airmozilla.manage.videoinfo import fetch_screencapture


def create_all_timestamp_pictures(event, verbose=False):
    assert event.duration
    timestamps = get_timenail_timestamps(event)
    groups = [timestamps[i:i + 10] for i in range(0, len(timestamps), 10)]
    for group in groups:
        create_timestamp_pictures(
            event,
            group,
            verbose=verbose,
        )


def create_timestamp_pictures(event, timestamps, verbose=False):
    fetch_screencapture(
        event,
        timestamps=timestamps,
        import_=True,
        import_immediately=True,
        verbose=verbose,
    )


def get_timenail_timestamps(event):
    assert event.duration
    # We have to avoid making too many thumbnails.
    # For a really long video you have to accept that there's going
    # to me bigger intervals between.
    #
    # For a video that is more than 1h30 we make it 60 sec.
    # That means a...
    # ... 1h45m will have 105 thumbnails.
    # ... 1h will have 80 thumbnails.
    # ... 30m will have 60 thumbnails
    # ...
    #
    # These numbers should ideally be done as a function
    # rather than a list of if-elif statements. Something
    # for the future.

    if event.duration > 60 * 60 + 60 * 30:
        incr = 60  # every minute
    elif event.duration > 60 * 60:
        incr = 45
    elif event.duration > 30 * 60:
        incr = 30
    elif event.duration > 60:
        incr = 10
    else:
        incr = 5

    at = 0
    timestamps = []
    while (at + incr) < event.duration:
        at += incr
        timestamps.append(at)
    return timestamps
