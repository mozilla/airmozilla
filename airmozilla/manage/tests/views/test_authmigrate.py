from nose.tools import ok_

from django.core.files import File
from django.contrib.auth import get_user_model

from airmozilla.main.models import (
    Event,
    SuggestedEvent,
    EventEmail,
    EventRevision,
    EventAssignment,
    SuggestedEventComment,
    EventTweet,
    Approval,
    Picture,
    Chapter,
)
from airmozilla.comments.models import (
    Comment,
    Unsubscription,
    Discussion,
    SuggestedDiscussion,
)
from airmozilla.search.models import (
    LoggedSearch,
    SavedSearch,
)
from airmozilla.starred.models import StarredEvent
from airmozilla.surveys.models import Survey, Question, Answer
from airmozilla.closedcaptions.models import (
    ClosedCaptions,
    RevInput,
    RevOrder,
)
from airmozilla.uploads.models import Upload
from airmozilla.manage.views.authmigrate import merge_user
from .base import ManageTestCase


User = get_user_model()


class TestAuthMigrate(ManageTestCase):

    def test_migrate_user(self):
        user = self.user
        event = Event.objects.get(title='Test event')
        event.creator = user
        event.save()

        Event.objects.create(
            title='Different',
            creator=User.objects.create(username='else'),
            modified_user=user,
            start_time=event.start_time,
        )

        EventEmail.objects.create(
            event=event,
            user=user,
            to='foo@bar.com',
        )

        EventRevision.objects.create(
            event=event,
            user=user,
            title='title'
        )

        EventTweet.objects.create(
            event=event,
            text='Hi',
            creator=user,
        )

        Approval.objects.create(
            event=event,
            user=user,
        )

        assignment = EventAssignment.objects.create(
            event=event
        )
        assignment.users.add(user)

        suggested_event = SuggestedEvent.objects.create(
            user=user,
            title='Something',
        )

        SuggestedEventComment.objects.create(
            suggested_event=suggested_event,
            comment='hi',
            user=user,
        )

        Comment.objects.create(
            event=event,
            comment='Hi!',
            user=user,
        )

        with open(self.main_image) as fp:
            Picture.objects.create(
                event=event,
                file=File(fp),
                modified_user=user,
            )

        Chapter.objects.create(
            event=event,
            timestamp=1,
            user=user,
        )

        LoggedSearch.objects.create(
            term='foo',
            user=user,
        )

        SavedSearch.objects.create(
            user=user,
            filters={'key': 'value'}
        )

        StarredEvent.objects.create(
            event=event,
            user=user,
        )

        survey = Survey.objects.create(
            name='name'
        )
        question = Question.objects.create(
            survey=survey,
            question={'key': 'value'},
        )
        Answer.objects.create(
            user=user,
            question=question,
            answer={'foo': 'bar'}
        )

        Upload.objects.create(
            user=user,
            url='https://',
            size=1234,
        )

        discussion = Discussion.objects.create(event=event)
        discussion.moderators.add(user)
        assert user in discussion.moderators.all()

        Unsubscription.objects.create(
            user=user,
            discussion=discussion,
        )

        sug_discussion = SuggestedDiscussion.objects.create(
            event=suggested_event
        )
        sug_discussion.moderators.add(user)
        assert user in sug_discussion.moderators.all()

        ClosedCaptions.objects.create(
            event=event,
            created_user=user,
        )

        RevOrder.objects.create(
            event=event,
            created_user=user,
            input=RevInput.objects.create(url='https://'),
            output_file_formats=['dfxp'],
        )

        new = User.objects.create(
            username='new',
            email='new@example.com'
        )

        # MOMENT OF TRUTH!
        things = merge_user(user, new)
        assert things

        # Events
        ok_(not Event.objects.filter(creator=user))
        ok_(Event.objects.filter(creator=new))
        ok_(not Event.objects.filter(modified_user=user))
        ok_(Event.objects.filter(modified_user=new))

        # EventEmail
        ok_(not EventEmail.objects.filter(user=user))
        ok_(EventEmail.objects.filter(user=new))

        # Suggested events
        ok_(not SuggestedEvent.objects.filter(user=user))
        ok_(SuggestedEvent.objects.filter(user=new))

        # Comments
        ok_(not Comment.objects.filter(user=user))
        ok_(Comment.objects.filter(user=new))

        # Discussion moderators
        ok_(new in discussion.moderators.all())
        ok_(user not in discussion.moderators.all())

        # Suggested Discussion moderators
        ok_(new in sug_discussion.moderators.all())
        ok_(user not in sug_discussion.moderators.all())

        # Unsubscriptions
        ok_(not Unsubscription.objects.filter(user=user))
        ok_(Unsubscription.objects.filter(user=new))

        # Suggested event
        ok_(not SuggestedEvent.objects.filter(user=user))
        ok_(SuggestedEvent.objects.filter(user=new))

        # Closed captions
        ok_(not ClosedCaptions.objects.filter(created_user=user))
        ok_(ClosedCaptions.objects.filter(created_user=new))

        # Rev orders
        ok_(not RevOrder.objects.filter(created_user=user))
        ok_(RevOrder.objects.filter(created_user=new))

        # Event revisions
        ok_(not EventRevision.objects.filter(user=user))
        ok_(EventRevision.objects.filter(user=new))

        # Event assignments
        ok_(new in assignment.users.all())
        ok_(user not in assignment.users.all())

        # Suggested event comments
        ok_(not SuggestedEventComment.objects.filter(user=user))
        ok_(SuggestedEventComment.objects.filter(user=new))

        # Event tweets
        ok_(not EventTweet.objects.filter(creator=user))
        ok_(EventTweet.objects.filter(creator=new))

        # Approvals
        ok_(not Approval.objects.filter(user=user))
        ok_(Approval.objects.filter(user=new))

        # Pictures
        ok_(not Picture.objects.filter(modified_user=user))
        ok_(Picture.objects.filter(modified_user=new))

        # Chapters
        ok_(not Chapter.objects.filter(user=user))
        ok_(Chapter.objects.filter(user=new))

        # Logged search
        ok_(not LoggedSearch.objects.filter(user=user))
        ok_(LoggedSearch.objects.filter(user=new))

        # Saved search
        ok_(not SavedSearch.objects.filter(user=user))
        ok_(SavedSearch.objects.filter(user=new))

        # Starred event
        ok_(not StarredEvent.objects.filter(user=user))
        ok_(StarredEvent.objects.filter(user=new))

        # (survey) Answers
        ok_(not Answer.objects.filter(user=user))
        ok_(Answer.objects.filter(user=new))

        # Uploads
        ok_(not Upload.objects.filter(user=user))
        ok_(Upload.objects.filter(user=new))

    def test_migrate_user_avoid_duplicate_m2ms(self):
        user = self.user
        new = User.objects.create(
            username='new',
            email='new@example.com'
        )
        other = User.objects.create(username='other')
        event = Event.objects.get(title='Test event')

        discussion = Discussion.objects.create(event=event)
        discussion.moderators.add(user)
        discussion.moderators.add(new)
        discussion.moderators.add(other)

        suggested_event = SuggestedEvent.objects.create(
            user=user,
            title='Something',
        )
        sug_discussion = SuggestedDiscussion.objects.create(
            event=suggested_event
        )
        sug_discussion.moderators.add(user)
        sug_discussion.moderators.add(new)
        sug_discussion.moderators.add(other)
        assert sug_discussion.moderators.all().count() == 3

        assignment = EventAssignment.objects.create(
            event=event
        )
        assignment.users.add(user)
        assignment.users.add(new)
        assignment.users.add(other)

        # MOMENT OF TRUTH!
        things = merge_user(user, new)
        assert things

        ok_(new in discussion.moderators.all())
        ok_(user not in discussion.moderators.all())
        assert discussion.moderators.all().count() == 2

        ok_(new in sug_discussion.moderators.all())
        ok_(user not in sug_discussion.moderators.all())
        assert sug_discussion.moderators.all().count() == 2

        ok_(new in assignment.users.all())
        ok_(user not in assignment.users.all())
        assert assignment.users.all().count() == 2
