# -*- coding: utf-8 -*-

import datetime
import random
import re
import os
import tempfile
import json
import string

from PIL import Image
from slugify import slugify
import requests

from django.core.files import File
from django.db import transaction
from django.utils import timezone
from django.conf import settings

from airmozilla.main import models as main_models
from airmozilla.uploads import models as upload_models


_here = os.path.dirname(__file__)
json_file = os.path.join(_here, 'random-data.json')
DATA = json.load(open(json_file))


def random_string(min_, max_=None):
    if max_ is None:
        max_ = min_

    length = random.randint(min_, max_)
    chars = []
    for __ in range(length):
        chars.append(random.choice(list(string.lowercase)))
    return ''.join(chars)


def random_past():
    now = timezone.now()
    return now - datetime.timedelta(days=random.randint(1, 400))


def random_slug_title():
    title_words = DATA['title_words']
    p = random.randint(0, len(title_words) - 10)
    length = random.randint(3, 10)
    words = title_words[p:p + length]
    title = ' '.join(words)
    title = title.title()  # funny
    title = title.strip()
    if not re.search('^[A-Z]', title):
        # try again
        return random_slug_title()
    slug = slugify(title.lower())
    return slug, title


def random_channels():
    channel_names = DATA['channel_names']
    channels = []
    for prob in (3, 8):  # thus might generate more than 1 non-main channel
        if random.randint(1, prob) == 1:
            # make it belong to a none-main channel
            name = random.choice(channel_names)
            slug = slugify(name.lower())
            channel, created = main_models.Channel.objects.get_or_create(
                slug=slug,
                name=name
            )
            if created and not channel.description:
                channel.description = "Here's the description for %s" % name
                channel.save()
            channels.append(channel)
    if random.randint(1, 5) != 1 or not channels:
        main, _ = main_models.Channel.objects.get_or_create(
            slug=settings.DEFAULT_CHANNEL_SLUG,
            name=settings.DEFAULT_CHANNEL_NAME
        )
        channels.append(main)
    return channels


def random_tags():
    names = set()
    tags_words = DATA['tags_words']
    for _ in range(random.randint(0, 5)):
        names.add(random.choice(tags_words))

    for name in names:
        tag, _ = main_models.Tag.objects.get_or_create(name=name)
        yield tag


vidly_template_content = """
{% if event.is_public() %}
{% set token = None %}
{% else %}
{% set token = vidly_tokenize(tag, 90) %}
{% endif %}
<script type="text/javascript" src="//vid.ly/{{ tag }}/em
bed{% if token %}?token={{ token }}{% endif %}"></script>
""".replace('em\nbed', 'embed').strip()

edgecast_template_content = (
    '<script src="//jwpsrv.com/library/_JGfOmN3EeOSkCIACrqE1A.js"></script>\n'
    '<script type="text/javascript">jwplayer.key="ZlZDNVcx3SYZWRdfbffTesf'
    'IPo+pT4L9/WniJa2YXSI=";</script>'
) + """
<div id="player"></div>
<script>
jwplayer("player").setup({
  file:"https://air.mozilla.org/edgecast.smil?venue={{ venue }}{% if not ev
ent.is_public() %}&token={{ edgecast_tokenize(seconds=90) }}{% endif %}",
  autostart: true,
  rtmp: { subscribe: true },
  image:"https://videos.cdn.mozilla.net/serv/air_mozilla/PleaseStandBy896.png",
  width:  896,
  height: 504,
  debug: false
 });
</script>
""".replace('ev\nent', 'event').strip()


def get_archive_template():
    name = "Vid.ly"
    try:
        return main_models.Template.objects.get(name=name)
    except main_models.Template.DoesNotExist:
        return main_models.Template.objects.create(
            name=name,
            content=vidly_template_content
        )


def get_live_template():
    name = "Edgecast"
    try:
        return main_models.Template.objects.get(name=name)
    except main_models.Template.DoesNotExist:
        return main_models.Template.objects.create(
            name=name,
            content=edgecast_template_content
        )


def random_start_time(span):
    days = random.randint(0, span)
    date = timezone.now().replace(microsecond=0, second=0)
    if random.randint(1, 4) == 1:
        date = date.replace(minute=30)
    elif random.randint(1, 4) == 1:
        date = date.replace(minute=45)
    elif random.randint(1, 4) == 1:
        date = date.replace(minute=15)
    else:
        date = date.replace(minute=0)

    # to prevent it all being on the same minute
    date += datetime.timedelta(hours=random.randint(-10, 20))
    if random.randint(1, 10) == 1:
        # let's make it a future day
        date += datetime.timedelta(days=days)
    else:
        date -= datetime.timedelta(days=days)
    return date


def random_status():
    # if it's a future event, we don't want to make it
    if random.randint(1, 12) == 1:
        return main_models.Event.STATUS_INITIATED
    if random.randint(1, 15) == 1:
        return main_models.Event.STATUS_REMOVED
    return main_models.Event.STATUS_SCHEDULED


def random_vidly_tag():
    return random.choice(DATA['vidly_tags'])


def url_to_localfile(url):
    dest = os.path.join(
        tempfile.gettempdir(),
        'airmozillafakedata'
    )
    if not os.path.isdir(dest):
        os.mkdir(dest)
    filename = os.path.basename(url)
    filepath = os.path.join(dest, filename)
    if not os.path.isfile(filepath):
        r = requests.get(url)
        assert r.status_code == 200, r.status_code
        with open(filepath, 'wb') as f:
            f.write(r.content)
    return filepath


def setup_gallery():
    gallery_pictures = DATA['gallery_pictures']
    if len(set(gallery_pictures)) != len(gallery_pictures):
        _once = set()
        for each in gallery_pictures:
            if each in _once:
                raise Exception("Duplicate picture %s" % each)
            _once.add(each)
    for url in random.sample(gallery_pictures, len(gallery_pictures)):
        try:
            filepath = url_to_localfile(url)
        except AssertionError as x:
            print "Skipping", url, x
            continue
        if main_models.Picture.objects.filter(notes=filepath[-100:]):
            # we already have this image
            continue
        image = Image.open(filepath)
        width, height = image.size
        with open(filepath, 'rb') as f:
            opened = File(f)
            picture = main_models.Picture(
                notes=filepath[-100:],
                size=opened.size,
                width=width,
                height=height,
            )
            picture.file.save(os.path.basename(filepath), opened, save=True)


def attach_picture(event):
    use_picture = random.randint(1, 4) != 1
    if use_picture:
        # most events get a picture from the gallery
        picture, = main_models.Picture.objects.all().order_by('?')[:1]
        event.picture = picture
        event.save()

    placeholder_pictures = DATA['placeholder_pictures']
    if not use_picture or random.randint(1, 4) == 1:
        # some events get a placeholder picture
        while True:
            try:
                filepath = url_to_localfile(
                    random.choice(placeholder_pictures)
                )
                break
            except AssertionError:
                # try again
                pass
        with open(filepath, 'rb') as f:
            opened = File(f)
            event.placeholder_img.save(
                os.path.basename(filepath),
                opened, save=True
            )

    assert event.picture or event.placeholder_img


def random_privacy():
    r = random.random()
    if r >= 0.8:
        # 20% chance it's company private
        return main_models.Event.PRIVACY_COMPANY
    if r >= 0.6:
        # 20% chance it's contributor privacy
        return main_models.Event.PRIVACY_CONTRIBUTORS
    return main_models.Event.PRIVACY_PUBLIC


def random_description(no_sents=5):
    sents = []
    words = DATA['title_words']
    for i in range(random.randint(2, no_sents)):
        start = random.randint(0, len(words) - 10)
        l = random.randint(3, 10)
        sents.append(' '.join(words[start: start + l]))
    return '. '.join([x.title() for x in sents])


def random_short_description():
    if random.randint(1, 2) == 1:
        return ''
    return random_description(no_sents=2)


def random_location():
    location, = (
        main_models.Location.objects.filter(is_active=True).order_by('?')[:1]
    )
    return location


def setup_locations():
    for name in DATA['locations']:
        if main_models.Location.objects.filter(name=name):
            # we already have this one
            continue

        is_active = random.randint(1, 4) != 1
        ts = random.choice(DATA['timezones'])
        main_models.Location.objects.create(
            name=name,
            timezone=ts,
            is_active=is_active,
        )


def setup_regions():
    picked = set()
    for name in DATA['regions']:
        locations = (
            main_models.Location.objects
            .exclude(id__in=picked)
            .order_by('?')[0:random.randint(0, 4)]
        )
        region = main_models.Region.objects.create(name=name)
        for l in locations:
            l.regions.add(region)
            picked.add(l.id)


def setup_users(howmany):
    for i in range(howmany):
        email = '%s-example@mozilla.com' % random_string(5, 15)
        try:
            main_models.User.objects.get(email=email)
        except main_models.User.DoesNotExist:
            main_models.User.objects.create(
                email=email,
                is_staff=random.randint(1, 20) == 1,
                username=random_string(20)
            )


def random_duration():
    if random.randint(1, 5) == 1:
        return None
    return random.randint(10, 200)


def create_vidlysubmission(event):
    if event.template_environment and event.template_environment.get('tag'):
        upload = random_upload(event)
        main_models.VidlySubmission.objects.create(
            tag=event.template_environment.get('tag'),
            event=event,
            url=upload.url,
            submission_time=random_past(),
            token_protection=event.privacy != main_models.Event.PRIVACY_PUBLIC,
        )


def random_upload(event):
    choices = DATA['video_urls']
    url = random.choice(choices)
    user, = main_models.User.objects.all().order_by('?')[:1]
    mime_types = {
        '.mp4': 'video/mp4',
        '.mov': 'video/quicktime',
        '.f4v': 'video/x-f4v',
        '.flv': 'video/x-flv',
        '.m4v': 'video/x-m4v',
        '.webm': 'video/webm',
    }
    mime_type = mime_types[os.path.splitext(url)[1]]
    return upload_models.Upload.objects.create(
        user=user,
        url=url,
        mime_type=mime_type,
        file_name=os.path.basename(url),
        size=random.randint(10000, 1000000),
        event=event
    )


def create_statistics(event):

    if event.status != main_models.Event.STATUS_SCHEDULED:
        return
    yesterday = timezone.now() - datetime.timedelta(days=1)
    if not event.archive_time or event.archive_time > yesterday:
        return

    submission = None
    for each in main_models.VidlySubmission.objects.filter(event=event):
        submission = each
        break
    else:
        return
    main_models.EventHitStats.objects.create(
        event=event,
        shortcode=submission.tag,
        total_hits=random.randint(10, 100000)
    )


@transaction.atomic
def generate(events=100, verbose=False):
    archive_template = get_archive_template()
    live_template = get_live_template()
    now = timezone.now()

    setup_gallery()
    setup_locations()
    setup_regions()
    setup_users(int(float(events) / 10))

    _slugs = set(
        main_models.Event.objects.all().values_list('slug', flat=True)
    )

    created_events = 0

    for _ in range(events):
        slug, title = random_slug_title()
        while slug in _slugs:
            slug += str(random.randint(1, 100))
        _slugs.add(slug)

        if verbose:  # pragma: no cover
            print (slug, title)
        channels = random_channels()
        tags = random_tags()
        start_time = random_start_time(events)

        if start_time > now:
            archive_time = None
            template = live_template
            template_environment = {'venue': 'AirMoMTV'}
        else:
            archive_time = start_time + datetime.timedelta(minutes=60)
            template = archive_template
            template_environment = {'tag': random_vidly_tag()}

        status = random_status()
        privacy = random_privacy()
        description = random_description()
        short_description = random_short_description()
        location = random_location()
        duration = random_duration()

        event = main_models.Event.objects.create(
            slug=slug,
            title=title,
            start_time=start_time,
            archive_time=archive_time,
            template=template,
            template_environment=template_environment,
            status=status,
            privacy=privacy,
            description=description,
            short_description=short_description,
            location=location,
            featured=random.randint(1, 20) == 1,
            duration=duration,
        )
        created_events += 1
        attach_picture(event)
        for t in tags:
            event.tags.add(t)
        for c in channels:
            event.channels.add(c)

        create_vidlysubmission(event)
        create_statistics(event)

    print "Created", created_events, "events"
    # raise Exception("Stopping there")
