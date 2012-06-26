import json

from django.conf import settings
from django.contrib.auth.models import User, Group
from django.test import TestCase

from funfactory.urlresolvers import reverse

from nose.tools import eq_, ok_

from airmozilla.main.models import Category, Event, Participant


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

    def setUp(self):
        User.objects.create_superuser('fake', 'fake@fake.com', 'fake')
        assert self.client.login(username='fake', password='fake')

    def test_event_request(self):
        """Event request responses and successful creation in the db."""
        response = self.client.get(reverse('manage:event_request'))
        eq_(response.status_code, 200)
        with open('airmozilla/manage/tests/firefox.png') as fp:
            response_ok = self.client.post(reverse('manage:event_request'),
                {
                    'title': 'Airmozilla Launch Test',
                    'video_url': 'http://www.mozilla.org',
                    'placeholder_img': fp,
                    'description': 'xxx',
                    'start_time': '8/20/2012 13:00',
                    'end_time': '8/20/2012 14:00',
                    'participants': 'Tim Mickel',
                    'location': 'Mountain View',
                    'category': '7',
                    'tags': 'airmozilla, test '
                }
            )
            response_fail = self.client.post(reverse('manage:event_request'),
                {
                    'title': 'Test fails, not enough data!',
                }
            )
        # update this when there is a proper success page for event requests
        self.assertRedirects(response_ok, reverse('manage:home'))
        eq_(response_fail.status_code, 200)
        event = Event.objects.get(title='Airmozilla Launch Test')
        eq_(event.video_url, 'http://www.mozilla.org/')

    def test_tag_autocomplete(self):
        """Autocomplete makes JSON for fixture tags and a nonexistent tag."""
        response = self.client.get(reverse('manage:tag_autocomplete'),
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
        response = self.client.get(reverse('manage:participant_autocomplete'),
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

    def test_event_edit(self):
        """The event editor page responds successfully."""
        response = self.client.get(reverse('manage:event_edit'))
        eq_(response.status_code, 200)


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
