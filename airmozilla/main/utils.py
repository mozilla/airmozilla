from collections import defaultdict

from airmozilla.main.models import Event, Channel


def get_event_channels(events):
    """
    Given an iterable of events (e.g. queryset), return a dict (based on
    collections.defaultdict) that maps event *objects* to *lists* of
    channel *objects*.
    """
    channels = defaultdict(list)

    events_paged_ids = dict((x.id, x) for x in events)
    mappings = Event.channels.through.objects.filter(
        event__in=events_paged_ids.keys()
    )
    # Next, set up a dict that maps each event id to an list of channel ids
    channel_ids = set()
    for each in mappings:
        channels[each.event_id].append(each.channel_id)
        channel_ids.add(each.channel_id)

    # Now, make a map of all actual channel objects once
    channel_maps = {}
    for channel in Channel.objects.filter(id__in=channel_ids):
        channel_maps[channel.id] = channel

    # lastly, convert the channels dict to be a map of event *instance*
    # to channel *instances* instead of just IDs.
    for event_id, channel_ids in channels.items():
        channels.pop(event_id)
        channels[events_paged_ids[event_id]] = [
            channel_maps[x] for x in channel_ids
        ]

    return channels
