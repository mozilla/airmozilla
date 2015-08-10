from django.contrib.auth.models import User

from nose.tools import eq_, ok_

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.main.models import Event
from airmozilla.surveys.models import Survey, Question, Answer


class SurveyTestCase(DjangoTestCase):

    def test_basic_save(self):
        survey = Survey.objects.create(name='Basic survey')
        event = Event.objects.get(title='Test event')
        survey.events.add(event)

        question = Question.objects.create(
            survey=survey,
            question={
                'some': 'json object'
            }
        )
        eq_(question.order, 1)
        ok_(question.modified)

        # test creating a second question to make sure the increment
        # works as expected
        second_question = Question.objects.create(
            survey=survey,
            question={
                'some': 'json object'
            }
        )
        eq_(second_question.order, 2)

        # the model should have a predetermined order
        eq_(
            list(Question.objects.all().values_list('order', flat=True)),
            [1, 2]
        )

        user, = User.objects.all()
        answer = Answer.objects.create(
            question=question,
            user=user,
            answer={
                'some': 'other json object'
            }
        )
        ok_(answer.modified)
