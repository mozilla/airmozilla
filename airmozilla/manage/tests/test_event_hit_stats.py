import datetime
from cStringIO import StringIO
from nose.tools import eq_, ok_
import mock

from django.utils import timezone

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.manage import event_hit_stats
from airmozilla.main.models import Event, EventHitStats, Template


SAMPLE_STATISTICS_XML = (
    '<?xml version="1.0"?>'
    '<Response><Message/><MessageCode/><Success><StatsInfo><StatsTable>'
    '<cols><col>Class</col><col>Vendor</col><col>Model</col>'
    '<col>Platform</col><col>OS</col><col>Browser</col><col>Browser Ver</col>'
    '<col>Hits</col></cols><rows><row><col>Desktop</col><col></col><col></col>'
    '<col></col><col>Apple</col><col>Firefox</col><col>21.0</col><col>5</col>'
    '</row><row><col>Desktop</col><col></col><col></col><col></col>'
    '<col>Apple</col><col>Firefox</col><col>20.0</col><col>2</col></row>'
    '</rows></StatsTable><Others>0</Others><TotalHits>%s</TotalHits>'
    '</StatsInfo></Success></Response>'
)


def non_signal_save(obj, **kwargs):
    obj.__class__.objects.filter(pk=obj.pk).update(**kwargs)


class EventHitStatsTestCase(DjangoTestCase):

    @mock.patch('urllib2.urlopen')
    def test_update(self, p_urlopen):

        calls = []

        def mocked_urlopen(request):
            calls.append(1)
            assert 'abc123' in request.data
            return StringIO((SAMPLE_STATISTICS_XML % (10,)).strip())

        p_urlopen.side_effect = mocked_urlopen

        assert not EventHitStats.objects.count()
        assert Event.objects.all()
        assert Event.objects.archived().all()

        eq_(event_hit_stats.update(), 0)
        assert not EventHitStats.objects.count()

        vidly_template = Template.objects.create(name='Vid.ly Template')
        event, = Event.objects.archived().all()
        event.template = vidly_template
        event.template_environment = {'tag': 'abc123'}
        event.save()

        eq_(event_hit_stats.update(), 1)
        assert EventHitStats.objects.count()
        stat, = EventHitStats.objects.all()
        eq_(stat.event, event)
        eq_(stat.total_hits, 10)
        eq_(stat.shortcode, 'abc123')
        eq_(len(calls), 1)

        # do it again and nothing should happen
        eq_(event_hit_stats.update(), 0)
        eq_(len(calls), 1)

        # let's pretend the event is half an hour old
        now = timezone.now()
        half_hour_ago = now - datetime.timedelta(minutes=30)

        # event.update(modified=event.modified - half_hour_ago)
        # non_signal_save(event, modified=half_hour_ago)

        eq_(event_hit_stats.update(), 0)
        eq_(len(calls), 1)
        # ...because the EventHitStats was modified too recently
        non_signal_save(stat, modified=half_hour_ago)
        non_signal_save(event, modified=half_hour_ago)
        eq_(event_hit_stats.update(), 0)
        eq_(len(calls), 1)

        # it needs to be at least one hour old
        hour_ago = now - datetime.timedelta(minutes=60, seconds=1)
        non_signal_save(stat, modified=hour_ago)
        non_signal_save(event, modified=hour_ago)

        eq_(event_hit_stats.update(), 1)
        eq_(len(calls), 2)

        # a second time, nothing should happen
        eq_(event_hit_stats.update(), 0)
        eq_(len(calls), 2)

        # let's pretend it's even older
        day_ago = now - datetime.timedelta(hours=24, seconds=1)
        non_signal_save(stat, modified=day_ago)
        non_signal_save(event, modified=day_ago)
        eq_(event_hit_stats.update(), 1)
        eq_(len(calls), 3)

        # second time, nothing should happen
        eq_(event_hit_stats.update(), 0)
        eq_(len(calls), 3)

        # even older still
        week_ago = now - datetime.timedelta(days=7, seconds=1)
        non_signal_save(stat, modified=week_ago)
        non_signal_save(event, modified=week_ago)
        eq_(event_hit_stats.update(), 1)
        eq_(len(calls), 4)

        # second time, nothing should happen
        eq_(event_hit_stats.update(), 0)
        eq_(len(calls), 4)

    @mock.patch('airmozilla.manage.event_hit_stats.logging')
    @mock.patch('urllib2.urlopen')
    def test_first_update_with_errors(self, p_urlopen, mock_logging):

        def mocked_urlopen(request):
            raise IOError('foo')

        p_urlopen.side_effect = mocked_urlopen

        vidly_template = Template.objects.create(name='Vid.ly Template')
        event, = Event.objects.archived().all()
        event.template = vidly_template
        event.template_environment = {'tag': ''}
        event.save()

        eq_(event_hit_stats.update(), 0)
        mock_logging.warn.assert_called_with(
            'Event %r does not have a Vid.ly tag',
            event.title
        )

        event.template_environment = {'tag': 'abc123'}
        event.save()

        self.assertRaises(
            IOError,
            event_hit_stats.update
        )

        eq_(event_hit_stats.update(swallow_errors=True), 0)
        mock_logging.error.assert_called_with(
            'Unable to download statistics for %r (tag: %s)',
            event.title,
            'abc123'
        )

    @mock.patch('urllib2.urlopen')
    def test_update_new_tag(self, p_urlopen):

        def mocked_urlopen(request):
            assert 'xyz987' in request.data
            return StringIO((SAMPLE_STATISTICS_XML % (10,)).strip())

        p_urlopen.side_effect = mocked_urlopen

        vidly_template = Template.objects.create(name='Vid.ly Template')
        event, = Event.objects.archived().all()
        event.template = vidly_template
        event.template_environment = {'tag': 'abc123'}
        event.save()

        stat = EventHitStats.objects.create(
            event=event,
            shortcode='abc123',
            total_hits=5,
        )

        event.template_environment = {'tag': 'xyz987'}
        event.save()

        # set them back two days
        now = timezone.now()
        days_ago = now - datetime.timedelta(hours=24 * 2, seconds=1)
        non_signal_save(stat, modified=days_ago)
        non_signal_save(
            event, modified=days_ago + datetime.timedelta(seconds=1)
        )

        eq_(event_hit_stats.update(), 1)
        stat = EventHitStats.objects.get(pk=stat.pk)
        eq_(stat.total_hits, 10)
        eq_(stat.shortcode, 'xyz987')

    @mock.patch('urllib2.urlopen')
    def test_update_removed_tag(self, p_urlopen):

        def mocked_urlopen(request):
            assert 'xyz987' in request.data
            return StringIO((SAMPLE_STATISTICS_XML % (10,)).strip())

        p_urlopen.side_effect = mocked_urlopen

        vidly_template = Template.objects.create(name='Vid.ly Template')
        event, = Event.objects.archived().all()
        event.template = vidly_template
        event.template_environment = {'tag': 'abc123'}
        event.save()

        stat = EventHitStats.objects.create(
            event=event,
            shortcode='abc123',
            total_hits=5,
        )

        event.template_environment = {'foo': 'bar'}
        event.save()

        # set them back two days
        now = timezone.now()
        days_ago = now - datetime.timedelta(hours=24 * 2, seconds=1)
        non_signal_save(stat, modified=days_ago)
        non_signal_save(
            event, modified=days_ago + datetime.timedelta(seconds=1)
        )

        eq_(event_hit_stats.update(), 0)
        ok_(not EventHitStats.objects.all().count())

    @mock.patch('airmozilla.manage.event_hit_stats.logging')
    @mock.patch('urllib2.urlopen')
    def test_update_with_errors(self, p_urlopen, mock_logging):

        def mocked_urlopen(request):
            raise IOError('boo!')

        p_urlopen.side_effect = mocked_urlopen

        vidly_template = Template.objects.create(name='Vid.ly Template')
        event, = Event.objects.archived().all()
        event.template = vidly_template
        event.template_environment = {'tag': 'abc123'}
        event.save()

        stat = EventHitStats.objects.create(
            event=event,
            shortcode='abc123',
            total_hits=5,
        )

        # set them back two days
        now = timezone.now()
        days_ago = now - datetime.timedelta(hours=24 * 2, seconds=1)
        non_signal_save(stat, modified=days_ago)
        non_signal_save(
            event, modified=days_ago + datetime.timedelta(seconds=1)
        )

        self.assertRaises(
            IOError,
            event_hit_stats.update
        )

        eq_(event_hit_stats.update(swallow_errors=True), 0)
        mock_logging.error.assert_called_with(
            'Unable to download statistics for %r (tag: %s)',
            event.title,
            'abc123'
        )
