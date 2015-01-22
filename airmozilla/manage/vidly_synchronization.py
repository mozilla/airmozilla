import datetime
from random import shuffle
from collections import defaultdict

from django.utils.timezone import utc

from airmozilla.main.models import Event, VidlySubmission
from airmozilla.manage import vidly


def synchronize_all(verbose=False):
    submissions = (
        VidlySubmission.objects
        .filter(event__template__name__icontains='Vid.ly')
        .filter(event__privacy=Event.PRIVACY_PUBLIC)
        .filter(token_protection=True)
    )

    tag_map = defaultdict(list)
    for submission in submissions:
        tag_map[submission.tag].append(submission)

    results = vidly.query(tag_map.keys())

    count_corrections = 0
    for tag, info in results.items():
        private = info['Private'] == 'true'
        for s in tag_map[tag]:
            if not private:
                if verbose:  # pragma: no cover
                    print (
                        "The VidlySubmission for (%r, %r) "
                        "was token protected by not according to Vid.ly" % (
                            s.event.title,
                            s.event.slug
                        )
                    )
                s.token_protection = False
                s.save()
                count_corrections += 1

    if verbose:  # pragma: no cover
        print (
            "Corrected %d vidly submissions' token protection\n" % (
                count_corrections,
            )
        )

    # Next we might have events that use tags that we have no
    # VidlySubmissions for.
    events = (
        Event.objects
        .filter(template__name__icontains='Vid.ly')
        .filter(template_environment__contains='"tag":')
    )
    event_map = defaultdict(list)
    for event in events:
        tag = event.template_environment['tag']
        event_map[tag].append(event)
    submission_tags = list(
        VidlySubmission.objects
        .filter(tag__in=event_map.keys())
        .values_list('tag', flat=True)
    )
    no_submission_tags = set(event_map.keys()) - set(submission_tags)
    no_submission_tags = list(no_submission_tags)
    if verbose:  # pragma: no cover
        print (
            "There are %d event tags we don't have vidly submissions for" % (
                len(no_submission_tags),
            )
        )
    shuffle(no_submission_tags)
    # let's not overload the Vid.ly query with doing too many lookups
    if len(no_submission_tags) > 100:
        no_submission_tags = no_submission_tags[:100]
        if verbose:  # pragma: no cover
            print "Capping to correct only 100 tags"
    results = vidly.query(no_submission_tags)
    count_creations = 0
    for tag in no_submission_tags:
        try:
            info = results[tag]
        except KeyError:
            if verbose:  # pragma: no cover
                for event in event_map[tag]:
                    print (
                        "(%s, %s) has tag %s but this does not exist on "
                        "Vid.ly" % (
                            event.title,
                            event.slug,
                            tag
                        )
                    )
            continue
        private = info['Private'] == 'true'
        hd = info['IsHD'] == 'true'
        created = info['Created']
        created = datetime.datetime.strptime(
            created,
            '%Y-%m-%d %H:%M:%S'
        )
        created = created.replace(tzinfo=utc)
        for event in event_map[tag]:
            assert not VidlySubmission.objects.filter(event=event, tag=tag)
            VidlySubmission.objects.create(
                event=event,
                tag=tag,
                token_protection=private,
                hd=hd,
                url=info['SourceFile'],
                email=info['UserEmail'],
                submission_time=created,
            )
            count_creations += 1

    if verbose:  # pragma: no cover
        print (
            "Created %d vidly submissions\n" % (
                count_creations,
            )
        )
