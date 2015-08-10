from nose.tools import ok_

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.main.models import Event
from airmozilla.subtitles.models import AmaraVideo

SAMPLE_TRANSCRIPT = {
    u'description': u'',
    u'language': {u'code': u'en', u'name': u'English'},
    u'metadata': {},
    u'note': u'From youtube',
    u'resource_uri':
        u'/api2/partners/videos/Yt8Od1dxtep1/languages/en/subtitles/',
    u'site_url': u'http://www.amara.org/videos/Yt8Od1dxtep1/en/706106/',
    u'sub_format': u'json',
    u'subtitles': [
        {u'end': 4367,
         u'meta': {u'new_paragraph': True},
         u'position': 1,
         u'start': 900,
         u'text': u"We like to call Firefox's address bar, the Awesome bar"},
        {u'end': 6900,
         u'meta': {u'new_paragraph': False},
         u'position': 2,
         u'start': 4368,
         u'text': u'because you can use it to find anything.'},
        {u'end': 10200,
         u'meta': {u'new_paragraph': False},
         u'position': 3,
         u'start': 6901,
         u'text': u'As you start to type in it, a list of websites appear'},
        {u'end': 13567,
         u'meta': {u'new_paragraph': False},
         u'position': 4,
         u'start': 10201,
         u'text': (u"based on where you've gone before and how often you went "
                   u"there.")},
        {u'end': 18633,
         u'meta': {u'new_paragraph': False},
         u'position': 5,
         u'start': 13568,
         u'text': (u"Sites that you've bookmarked or tagged are highlighted "
                   u"to make the list easy to scan.")},
        {u'end': 22300,
         u'meta': {u'new_paragraph': False},
         u'position': 6,
         u'start': 18634,
         u'text': (u"Just click one of the sites and you'll be taken there "
                   u"instantly.")},
        {u'end': 25367,
         u'meta': {u'new_paragraph': False},
         u'position': 7,
         u'start': 22301,
         u'text': u'And the Awesome bar gets better the more you use it.'},
        {u'end': 29400,
         u'meta': {u'new_paragraph': False},
         u'position': 8,
         u'start': 25368,
         u'text': (u'You can often find the site you want after typing just '
                   'one letter.')},
        {u'end': 31200,
         u'meta': {u'new_paragraph': False},
         u'position': 9,
         u'start': 29401,
         u'text': u"But wait, there's more!"},
        {u'end': 36067,
         u'meta': {u'new_paragraph': False},
         u'position': 10,
         u'start': 31201,
         u'text': (u'You can also search the web from here. Just type a '
                   u'search term and hit enter.')},
        {u'end': 40067,
         u'meta': {u'new_paragraph': False},
         u'position': 11,
         u'start': 36068,
         u'text': (u'The awesome bar makes it easy to do more surfing with '
                   u'less typing.')}],
    u'title': u'',
    u'version_no': 1,
    u'version_number': 1,
    u'video': u'Firefox Awesome Bar - Find your boo...',
    u'video_description': u'',
    u'video_title': u''
}


class AmaraVideoTestCase(DjangoTestCase):

    def test_basic_save(self):
        event = Event.objects.get(title='Test event')
        amara_video = AmaraVideo.objects.create(
            event=event,
            video_url='https://www.youtube.com/watch?v=qf0SNKwZ_SY',
            video_id='LaXSpZ3FQJps',
            transcript=SAMPLE_TRANSCRIPT
        )

        ok_(amara_video.video_id in amara_video.url())

        # reload the event and it should now have a transcript
        event = Event.objects.get(pk=event.pk)
        ok_(event.transcript)
        ok_(
            u"We like to call Firefox's address bar, the Awesome bar"
            in event.transcript
        )
