import datetime
import os
import re
import tempfile
import urllib2

from lxml import etree
from optparse import make_option
from tempfile import gettempdir


from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import utc

from airmozilla.main.models import Event, Tag, Template

DEFAULT_VIDLY_TEMPLATE = """
<video controls width="100%" controls preload="none" poster="https://d3fenhwk93s16g.cloudfront.net/{{ tag }}/poster.jpg">
    <source src="http://cf.cdn.vid.ly/{{ tag }}/mp4.mp4" type="video/mp4">
    <source src="http://cf.cdn.vid.ly/{{ tag }}/webm.webm" type="video/webm">
    <source src="http://cf.cdn.vid.ly/{{ tag }}/ogv.ogv" type="video/ogg">
    <a target="_blank" href="http://vid.ly/{{ tag }}"><img src="https://d3fenhwk93s16g.cloudfront.net/{{ tag }}/poster.jpg" width="500" alt="Video"></a>
</video>
"""
DEFAULT_VIDLY_NAME = "Vid.ly"

DEFAULT_OGG_TEMPLATE = """
<video width="620" height="350" controls="controls">
  <source src="{{ url }}" type="video/ogg" />
</video>
"""
DEFAULT_OGG_NAME = "Ogg Video"


class Command(BaseCommand):
    args = '<wordpress_xml_dump.xml> <default_thumb>'
    option_list = BaseCommand.option_list + (
        make_option('--clear',
            action='store_true',
            dest='clear',
            default=False,
            help='Clear all events before running the migration.'),
    )
    nsmap = {
        'wp': 'http://wordpress.org/export/1.2/',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'content': 'http://purl.org/rss/1.0/modules/content/',
        'excerpt': 'http://wordpress.org/export/1.2/excerpt/'
    }
    import_cache = tempfile.gettempdir()

    def _check_video_templates(self):
        # make sure we have some assumed Video templates in the database
        try:
            Template.objects.get(name=DEFAULT_VIDLY_NAME)
        except Template.DoesNotExist:
            Template.objects.create(
                name=DEFAULT_VIDLY_NAME,
                content=DEFAULT_VIDLY_TEMPLATE
            )
        try:
            Template.objects.get(name=DEFAULT_OGG_NAME)
        except Template.DoesNotExist:
            Template.objects.create(
                name=DEFAULT_OGG_NAME,
                content=DEFAULT_OGG_TEMPLATE
            )

    def handle(self, *args, **options):
        if options['clear']:
            for e in Event.objects.all():
                e.delete()
        self._check_video_templates()
        attachments = {}
        try:
            wordpress_xml_dump = args[0]
            item_parser = etree.iterparse(wordpress_xml_dump, tag='item')
        except IndexError:
            raise CommandError('Please provide an XML dump.')
        except IOError:
            raise CommandError('The provided file does not exist or is not'
                               ' a valid Wordpress XML dump')
        try:
            self.default_thumb_path = args[1]
            self.default_thumb = open(self.default_thumb_path, 'rb')
        except IOError:
            raise CommandError('Please provide a valid default thumbnail.')

        for _, element in item_parser:
            fields = {
                'title': 'title',
                'status': 'wp:status',
                'start_time': 'pubDate',
                'description': 'content:encoded',
                'short_description': 'excerpt:encoded',
                'created': 'wp:post_date',
                'slug': 'wp:post_name',
                'type': 'wp:post_type',
                'attachment': 'wp:attachment_url',
                'post_id': 'wp:post_id'
            }
            item = self.extract_item(element, fields)
            if Event.objects.filter(slug=item['slug']).exists():
                self.stdout.write(
                    'Event %s already exists, skipping.\n' % item['slug']
                )
                continue

            if item['type'] == 'attachment':
                # The item is a thumbnail attachment; save for later
                attachments[item['post_id']] = item['attachment']
            elif item['type'] == 'post':
                # Create and initiate a new event
                event = Event()
                event.title = item['title']
                event.slug = item['slug']
                try:
                    event.start_time = datetime.datetime.strptime(
                        item['start_time'],
                        '%a, %d %b %Y %H:%M:%S +0000'
                    ).replace(tzinfo=utc)
                except ValueError:
                    event.start_time = datetime.datetime.strptime(
                        item['created'],
                        '%Y-%m-%d %H:%M:%S'
                    ).replace(tzinfo=utc)
                event.archive_time = (
                    event.start_time + datetime.timedelta(hours=1)
                )
                # Set status & public status from WP metadata
                event.status = Event.STATUS_INITIATED
                event.public = False
                if item['status'] == 'publish':
                    event.status = Event.STATUS_SCHEDULED
                    event.public = True
                elif item['status'] == 'private':
                    event.status = Event.STATUS_SCHEDULED
                elif item['status'] == 'trash':
                    event.status = Event.STATUS_REMOVED
                # Parse out the video from the event description
                event.description = 'n/a'
                if item['description']:
                    self.parse_description(event, item['description'])
                event.short_description = item['short_description'] or ''
                # Add thumbnail and save
                thumbnail_id = 0
                for meta in element.findall('wp:postmeta',
                                            namespaces=self.nsmap):
                    meta_key, meta_val = meta.getchildren()
                    if meta_key.text == '_thumbnail_id':
                        thumbnail_id = meta_val.text
                if thumbnail_id in attachments:
                    self.attach_thumbnail(event, attachments[thumbnail_id])
                else:
                    self.attach_thumbnail(event)
                    self.stdout.write(
                        'No thumb found for %s, used default.\n' % event.slug
                    )
                event.save()
                self.stdout.write('Saved event %s\n' % event.slug)

    def extract_item(self, element, fields):
        """Returns a shortcut dictionary of element's children parsed
           according to fields (destination_key: source_child_tag)."""
        item = {}
        for name, tag in fields.iteritems():
            child = element.find(tag, namespaces=self.nsmap)
            try:
                item[name] = child.text.encode('utf-8').strip()
            except AttributeError:
                item[name] = None
        return item

    def parse_description(self, event, description_raw):
        """Parse out video embeds from the description, correctly set
           templates and their environments; leave descriptions clean."""
        vidly_tag = re.compile('\[vidly code="(\w+)?"\]')
        vidly_template = Template.objects.get(name='Vid.ly')
        ogg_tag = re.compile('<video src="([^"]*)".*?>')
        ogg_template = Template.objects.get(name='Ogg Video')

        event.description = description_raw
        vidly_search = vidly_tag.search(description_raw)
        ogg_search = ogg_tag.search(description_raw)
        if vidly_search:
            event.description = event.description.replace(
                vidly_search.group(0), ''
            )
            event.template = vidly_template
            event.template_environment = {'tag': vidly_search.group(1)}
        elif ogg_search:
            event.description = event.description.replace(
                ogg_search.group(0), ''
            )
            event.template = ogg_template
            event.template_environment = {'url': ogg_search.group(1)}
        else:
            event.status = Event.STATUS_REMOVED
        event.description = event.description.strip()

    def attach_thumbnail(self, event, url=None):
        """Download, cache, and attach an event's placeholder image."""
        if not url:
            # Use a default image, provided
            _, ext = os.path.splitext(self.default_thumb_path)
            img_temp = File(self.default_thumb)
        else:
            _, ext = os.path.splitext(url)
            cache_path = os.path.join(self.import_cache, event.slug) + ext
            try:
                # Read a cached image
                img_temp = File(
                    open(cache_path, 'rb')
                )
            except IOError:
                # Download and create the image
                img_temp = File(
                    open(cache_path, 'wb+')
                )
                img_temp.write(urllib2.urlopen(url).read())
                img_temp.flush()
        event.placeholder_img.save('img%s' % ext, img_temp)
