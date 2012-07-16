import datetime
import json
import pytz

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.test import TestCase

from funfactory.urlresolvers import reverse

from nose.tools import eq_, ok_

from airmozilla.main.models import (Approval, Category, Event, EventOldSlug,
                                    Participant, Template)


class TestPermissions(TestCase):
    def _login(self, is_staff):
        user = User.objects.create_user('fake', 'fake@fake.com', 'fake')
        user.is_staff = is_staff
        user.save()
        assert self.client.login(username='fake', password='fake')
        return user

    def test_unauthorized(self):
        """ Client with no log in - should be rejected. """
        response = self.client.get(reverse('manage:home'))
        self.assertRedirects(response, settings.LOGIN_URL
                             + '?next=' + reverse('manage:home'))

    def test_not_staff(self):
        """ User is not staff - should be rejected. """
        self._login(is_staff=False)
        response = self.client.get(reverse('manage:home'))
        self.assertRedirects(response, settings.LOGIN_URL
                             + '?next=' + reverse('manage:home'))

    def test_staff_home(self):
        """ User is staff - should get an OK homepage. """
        self._login(is_staff=True)
        response = self.client.get(reverse('manage:home'))
        eq_(response.status_code, 200)

    def test_staff_logout(self):
        """ Log out makes admin inaccessible. """
        self._login(is_staff=True)
        self.client.get(reverse('auth:logout'))
        response = self.client.get(reverse('manage:home'))
        self.assertRedirects(response, settings.LOGIN_URL
                             + '?next=' + reverse('manage:home'))

    def test_edit_user(self):
        """ Unprivileged admin - shouldn't see user change page. """
        self._login(is_staff=True)
        response = self.client.get(reverse('manage:users'))
        self.assertRedirects(response, settings.LOGIN_URL
                             + '?next=' + reverse('manage:users'))


class TestUsersAndGroups(TestCase):
    def setUp(self):
        User.objects.create_superuser('fake', 'fake@fake.com', 'fake')
        assert self.client.login(username='fake', password='fake')

    def test_user_group_pages(self):
        """User and group listing pages respond with success."""
        response = self.client.get(reverse('manage:users'))
        eq_(response.status_code, 200)
        response = self.client.get(reverse('manage:users'), {'page': 5000})
        eq_(response.status_code, 200)
        response = self.client.get(reverse('manage:groups'))
        eq_(response.status_code, 200)

    def test_user_edit(self):
        """Add superuser and staff status via the user edit form."""
        user = User.objects.create_user('no', 'no@no.com', 'no')
        response = self.client.post(reverse('manage:user_edit',
                                            kwargs={'id': user.id}),
            {
                'is_superuser': 'on',
                'is_staff': 'on',
                'is_active': 'on'
            }
        )
        self.assertRedirects(response, reverse('manage:users'))
        user = User.objects.get(id=user.id)
        ok_(user.is_superuser)
        ok_(user.is_staff)

    def test_group_add(self):
        """Add a group and verify its creation."""
        response = self.client.get(reverse('manage:group_new'))
        eq_(response.status_code, 200)
        response = self.client.post(reverse('manage:group_new'),
            {
                'name': 'fake_group'
            }
        )
        self.assertRedirects(response, reverse('manage:groups'))
        group = Group.objects.get(name='fake_group')
        ok_(group is not None)
        eq_(group.name, 'fake_group')

    def test_group_edit(self):
        """Group editing: group name change form sucessfully changes name."""
        group, __ = Group.objects.get_or_create(name='testergroup')
        response = self.client.get(reverse('manage:group_edit',
                                           kwargs={'id': group.id}))
        eq_(response.status_code, 200)
        response = self.client.post(reverse('manage:group_edit',
                                            kwargs={'id': group.id}),
            {
                'name': 'newtestergroup  '
            }
        )
        self.assertRedirects(response, reverse('manage:groups'))
        group = Group.objects.get(id=group.id)
        eq_(group.name, 'newtestergroup')

    def test_user_search(self):
        """Searching for a created user redirects properly; otherwise fail."""
        user = User.objects.create_user('t', 'testuser@mozilla.com')
        response_ok = self.client.post(reverse('manage:users'),
            {
                'email': user.email
            }
        )
        self.assertRedirects(response_ok, reverse('manage:user_edit',
                                               kwargs={'id': user.id}))
        response_fail = self.client.post(reverse('manage:users'),
            {
                'email': 'bademail@mozilla.com'
            }
        )
        eq_(response_fail.status_code, 200)


class TestEvents(TestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']
    event_base_data = {
        'status': Event.STATUS_SCHEDULED,
        'description': '...',
        'participants': 'Tim Mickel',
        'location': 'Mountain View',
        'category': '7',
        'tags': 'xxx',
        'template': '1',
        'start_time': '2012-3-4 12:00',
        'timezone': 'US/Pacific'
    }
    placeholder = 'airmozilla/manage/tests/firefox.png'

    def setUp(self):
        User.objects.create_superuser('fake', 'fake@fake.com', 'fake')
        assert self.client.login(username='fake', password='fake')

    def test_event_request(self):
        """Event request responses and successful creation in the db."""
        response = self.client.get(reverse('manage:event_request'))
        eq_(response.status_code, 200)
        with open(self.placeholder) as fp:
            response_ok = self.client.post(
                reverse('manage:event_request'),
                dict(self.event_base_data, placeholder_img=fp,
                     title='Airmozilla Launch Test')
            )
            response_fail = self.client.post(
                reverse('manage:event_request'),
                {
                    'title': 'Test fails, not enough data!',
                }
            )
        # update this when there is a proper success page for event requests
        self.assertRedirects(response_ok, reverse('manage:home'))
        eq_(response_fail.status_code, 200)
        event = Event.objects.get(title='Airmozilla Launch Test')
        eq_(event.location, 'Mountain View')

    def test_tag_autocomplete(self):
        """Autocomplete makes JSON for fixture tags and a nonexistent tag."""
        response = self.client.get(
            reverse('manage:tag_autocomplete'),
            {
                'q': 'tes'
            }
        )
        eq_(response.status_code, 200)
        parsed = json.loads(response.content)
        ok_('tags' in parsed)
        tags = [t['text'] for t in parsed['tags'] if 'text' in t]
        eq_(len(tags), 3)
        ok_(('tes' in tags) and ('test' in tags) and ('testing' in tags))

    def test_participant_autocomplete(self):
        """Autocomplete makes JSON pages and correct results for fixtures."""
        response = self.client.get(
            reverse('manage:participant_autocomplete'),
            {
                'q': 'Ti'
            }
        )
        eq_(response.status_code, 200)
        parsed = json.loads(response.content)
        ok_('participants' in parsed)
        participants = [p['text'] for p in parsed['participants']
                            if 'text' in p]
        eq_(len(participants), 1)
        ok_('Tim Mickel' in participants)
        response_fail = self.client.get(
            reverse('manage:participant_autocomplete'),
            {
                'q': 'ickel'
            }
        )
        eq_(response_fail.status_code, 200)
        parsed_fail = json.loads(response_fail.content)
        eq_(parsed_fail, {'participants': []})

    def test_events(self):
        """The events page responds successfully."""
        response = self.client.get(reverse('manage:events'))
        eq_(response.status_code, 200)

    def test_find_event(self):
        """Find event responds with filtered results or raises error."""
        response_ok = self.client.post(reverse('manage:events'),
                                       {'title': 'test'})
        eq_(response_ok.status_code, 200)
        ok_(response_ok.content.find('Test event') >= 0)
        response_fail = self.client.post(reverse('manage:events'),
                                         {'title': 'laskdjflkajdsf'})
        eq_(response_fail.status_code, 200)
        ok_(response_fail.content.find('No event') >= 0)

    def test_event_edit_slug(self):
        """Test editing an event - modifying an event's slug
           results in a correct EventOldSlug."""
        event = Event.objects.get(title='Test event')
        response = self.client.get(reverse('manage:event_edit',
                                           kwargs={'id': event.id}))
        eq_(response.status_code, 200)
        response_ok = self.client.post(
            reverse('manage:event_edit', kwargs={'id': event.id}),
            dict(self.event_base_data, title='Tested event')
        )
        self.assertRedirects(response_ok, reverse('manage:events'))
        ok_(EventOldSlug.objects.get(slug='test-event', event=event))
        event = Event.objects.get(title='Tested event')
        eq_(event.slug, 'tested-event')
        response_fail = self.client.post(
            reverse('manage:event_edit', kwargs={'id': event.id}),
            {
                'title': 'not nearly enough data',
                'status': Event.STATUS_SCHEDULED
            }
        )
        eq_(response_fail.status_code, 200)

    def test_event_edit_templates(self):
        """Event editing results in correct template environments."""
        event = Event.objects.get(title='Test event')
        url = reverse('manage:event_edit', kwargs={'id': event.id})
        response_ok = self.client.post(
            url,
            dict(self.event_base_data, title='template edit',
                 template_environment='tv1=\'hi\'\ntv2===')
        )
        self.assertRedirects(response_ok, reverse('manage:events'))
        event = Event.objects.get(id=event.id)
        eq_(event.template_environment, {'tv1': "'hi'", 'tv2': '=='})
        response_edit_page = self.client.get(url)
        eq_(response_edit_page.status_code, 200,
            'Edit page renders OK with a specified template environment.')
        response_fail = self.client.post(url,
            dict(self.event_base_data, title='template edit',
                 template_environment='failenvironment'))
        eq_(response_fail.status_code, 200)

    def test_timezones(self):
        """Event requests/edits demonstrate correct timezone math."""
        utc = pytz.timezone('UTC')

        def _tz_test(url, tzdata, correct_date, msg):
            with open(self.placeholder) as fp:
                base_data = dict(self.event_base_data,
                                 title='timezone test', placeholder_img=fp)
                self.client.post(url, dict(base_data, **tzdata))
            event = Event.objects.get(title='timezone test',
                                      start_time=correct_date)
            ok_(event, msg + ' vs. ' + str(event.start_time))
        url = reverse('manage:event_request')
        _tz_test(
            url,
            {
                'start_time': '2012-08-03 12:00',
                'timezone': 'US/Eastern'
            },
            datetime.datetime(2012, 8, 3, 16).replace(tzinfo=utc),
            'Event request summer date - Eastern UTC-04 input'
        )
        _tz_test(
            url,
            {
                'start_time': '2012-11-30 3:00',
                'timezone': 'Europe/Paris'
            },
            datetime.datetime(2012, 11, 30, 2).replace(tzinfo=utc),
            'Event request winter date - CET UTC+01 input'
        )
        event = Event.objects.get(title='Test event')
        url = reverse('manage:event_edit', kwargs={'id': event.id})
        _tz_test(
            url,
            {
                'start_time': '2012-08-03 15:00',
                'timezone': 'US/Pacific'
            },
            datetime.datetime(2012, 8, 3, 22).replace(tzinfo=utc),
            'Modify event summer date - Pacific UTC-07 input'
        )
        _tz_test(
            url,
            {
                'start_time': '2012-12-25 15:00',
                'timezone': 'US/Pacific'
            },
            datetime.datetime(2012, 12, 25, 23).replace(tzinfo=utc),
            'Modify event winter date - Pacific UTC-08 input'
        )


class TestParticipants(TestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']

    def setUp(self):
        User.objects.create_superuser('fake', 'fake@fake.com', 'fake')
        assert self.client.login(username='fake', password='fake')

    def test_participant_pages(self):
        """Participants pagination always returns valid pages."""
        response = self.client.get(reverse('manage:participants'))
        eq_(response.status_code, 200)
        response = self.client.get(reverse('manage:participants'),
                                   {'page': 5000})
        eq_(response.status_code, 200)

    def test_participant_find(self):
        """Search filters participants; returns all for bad search."""
        response_ok = self.client.post(reverse('manage:participants'),
            {
                'name': 'Tim'
            }
        )
        eq_(response_ok.status_code, 200)
        ok_(response_ok.content.find('Tim') >= 0)
        response_fail = self.client.post(reverse('manage:participants'),
            {
                'name': 'Lincoln'
            }
        )
        eq_(response_fail.status_code, 200)
        ok_(response_fail.content.find('Tim') >= 0)

    def test_participant_edit(self):
        """Participant edit page responds OK; bad form results in failure;
        submission induces a change.
        """
        participant = Participant.objects.get(name='Tim Mickel')
        response = self.client.get(reverse('manage:participant_edit',
                                           kwargs={'id': participant.id}))
        eq_(response.status_code, 200)
        response_ok = self.client.post(reverse('manage:participant_edit',
                                               kwargs={'id': participant.id}),
            {
                'name': 'George Washington',
                'email': 'george@whitehouse.gov',
                'role': Participant.ROLE_PRINCIPAL_PRESENTER,
                'cleared': Participant.CLEARED_YES
            }
        )
        self.assertRedirects(response_ok, reverse('manage:participants'))
        participant_george = Participant.objects.get(id=participant.id)
        eq_(participant_george.name, 'George Washington')
        response_fail = self.client.post(reverse('manage:participant_edit',
                                                kwargs={'id': participant.id}),
            {
                'name': 'George Washington',
                'email': 'bademail'
            }
        )
        eq_(response_fail.status_code, 200)

    def test_participant_new(self):
        """New participant page responds OK and form works as expected."""
        response = self.client.get(reverse('manage:participant_new'))
        eq_(response.status_code, 200)
        with open('airmozilla/manage/tests/firefox.png') as fp:
            response_ok = self.client.post(reverse('manage:participant_new'),
                {
                    'name': 'Mozilla Firefox',
                    'slug': 'mozilla-firefox',
                    'photo': fp,
                    'email': 'mozilla@mozilla.com',
                    'role': Participant.ROLE_PRINCIPAL_PRESENTER,
                    'cleared': Participant.CLEARED_NO
                }
            )
        self.assertRedirects(response_ok, reverse('manage:participants'))
        participant = Participant.objects.get(name='Mozilla Firefox')
        eq_(participant.email, 'mozilla@mozilla.com')


class TestCategories(TestCase):
    def setUp(self):
        User.objects.create_superuser('fake', 'fake@fake.com', 'fake')
        assert self.client.login(username='fake', password='fake')

    def test_categories(self):
        """ Categories listing responds OK. """
        response = self.client.get(reverse('manage:categories'))
        eq_(response.status_code, 200)

    def test_category_new(self):
        """ Category form adds new categories. """
        response_ok = self.client.post(reverse('manage:categories'),
            {
                'name': 'Web Dev Talks '
            }
        )
        eq_(response_ok.status_code, 200)
        ok_(Category.objects.get(name='Web Dev Talks'))
        response_fail = self.client.post(reverse('manage:categories'))
        eq_(response_fail.status_code, 200)


class TestTemplates(TestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']

    def setUp(self):
        User.objects.create_superuser('fake', 'fake@fake.com', 'fake')
        assert self.client.login(username='fake', password='fake')

    def test_templates(self):
        """Templates listing responds OK."""
        response = self.client.get(reverse('manage:templates'))
        eq_(response.status_code, 200)

    def test_template_new(self):
        """New template form responds OK and results in a new template."""
        url = reverse('manage:template_new')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_ok = self.client.post(url, {
            'name': 'happy template',
            'content': 'hello!'
        })
        self.assertRedirects(response_ok, reverse('manage:templates'))
        ok_(Template.objects.get(name='happy template'))
        response_fail = self.client.post(url)
        eq_(response_fail.status_code, 200)

    def test_template_edit(self):
        """Template editor response OK, results in changed data or fail."""
        template = Template.objects.get(name='test template')
        url = reverse('manage:template_edit', kwargs={'id': template.id})
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_ok = self.client.post(url, {
            'name': 'new name',
            'content': 'new content'
        })
        self.assertRedirects(response_ok, reverse('manage:templates'))
        template = Template.objects.get(id=template.id)
        eq_(template.content, 'new content')
        response_fail = self.client.post(url, {
            'name': 'no content'
        })
        eq_(response_fail.status_code, 200)

    def test_template_remove(self):
        """Deleting a template works correctly."""
        template = Template.objects.get(name='test template')
        url = reverse('manage:template_remove', kwargs={'id': template.id})
        self.client.get(url)
        template = Template.objects.get(id=template.id)
        ok_(template)  # the template wasn't deleted because we didn't use POST
        response_ok = self.client.post(url)
        self.assertRedirects(response_ok, reverse('manage:templates'))
        template = Template.objects.filter(id=template.id).exists()
        ok_(not template)

    def test_template_env_autofill(self):
        """The JSON autofiller responds correctly for the fixture template."""
        template = Template.objects.get(name='test template')
        response = self.client.get(reverse('manage:template_env_autofill'),
                                   {'template': template.id})
        eq_(response.status_code, 200)
        template_parsed = json.loads(response.content)
        ok_(template_parsed)
        eq_(template_parsed, {'variables': 'tv1=\ntv2='})


class TestApprovals(TestCase):
    fixtures = ['airmozilla/manage/tests/main_testdata.json']
    
    def setUp(self):
        User.objects.create_superuser('fake', 'fake@fake.com', 'fake')
        assert self.client.login(username='fake', password='fake')

    def test_approvals(self):
        response = self.client.get(reverse('manage:approvals'))
        eq_(response.status_code, 200)

    def test_approval_review(self):
        app = Approval(event=Event.objects.get(id=22),
                       group=Group.objects.get(id=1))
        app.save()
        url = reverse('manage:approval_review', kwargs={'id': app.id})
        response_not_in_group = self.client.get(url)
        self.assertRedirects(response_not_in_group,
                             reverse('manage:approvals'))
        User.objects.get(username='fake').groups.add(1)
        response = self.client.get(url)
        eq_(response.status_code, 200)
        response_approve = self.client.post(url, {'approve': 'approve'})
        self.assertRedirects(response_approve, reverse('manage:approvals'))
        app = Approval.objects.get(id=app.id)
        ok_(app.approved)
        ok_(app.processed)
        eq_(app.user, User.objects.get(username='fake'))
