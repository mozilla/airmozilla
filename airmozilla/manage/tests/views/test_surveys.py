import json

from nose.tools import eq_, ok_

from funfactory.urlresolvers import reverse

from airmozilla.main.models import Event
from airmozilla.surveys.models import Survey, Question
from .base import ManageTestCase


class TestCase(ManageTestCase):

    def test_create_survey(self):
        event = Event.objects.get(title='Test event')
        url = reverse('manage:event_edit', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        url = reverse('manage:event_survey', args=(event.pk,))
        ok_(url in response.content)

        # click that button
        response = self.client.get(url)
        eq_(response.status_code, 200)

    def test_create_and_delete_question(self):
        event = Event.objects.get(title='Test event')
        survey = Survey.objects.create(event=event)
        url = reverse(
            'manage:event_survey_question_new', args=(event.id,)
        )

        response = self.client.post(url, {})
        eq_(response.status_code, 302)
        question = Question.objects.get(survey=survey)
        url = reverse(
            'manage:event_survey_question_delete',
            args=(event.id, question.id)
        )
        response = self.client.post(url)
        eq_(response.status_code, 302)
        ok_(not Question.objects.filter(survey=survey))

    def test_edit_question(self):
        event = Event.objects.get(title='Test event')
        survey = Survey.objects.create(event=event)
        question = Question.objects.create(survey=survey)
        url = reverse(
            'manage:event_survey_question_edit',
            args=(event.id, question.id)
        )
        q = {
            'question': '?',
            'choices': ['a', 'b']
        }
        payload = json.dumps(q)
        response = self.client.post(url, {'question': payload})
        eq_(response.status_code, 200)
        eq_(
            json.loads(response.content),
            {'question': json.dumps(q, indent=2)}
        )
        # reload
        question = Question.objects.get(id=question.id)
        eq_(question.question, q)

        # bad edit
        payload = payload.replace('{', 'x')
        response = self.client.post(url, {'question': payload})
        eq_(response.status_code, 200)
        error = json.loads(response.content)['error']
        ok_('No JSON object could be decoded' in error[0])

    def test_ordering_questions(self):
        event = Event.objects.get(title='Test event')
        survey = Survey.objects.create(event=event)
        question_1 = Question.objects.create(
            survey=survey,
            question={'one': 1}
        )
        question_2 = Question.objects.create(
            survey=survey,
            question={'two': 2}
        )
        question_3 = Question.objects.create(
            survey=survey,
            question={'three': 3}
        )
        questions = list(Question.objects.filter(survey=survey))
        eq_(questions, [question_1, question_2, question_3])
        # let's move question_2 up one
        url = reverse(
            'manage:event_survey_question_edit',
            args=(event.id, question_2.id)
        )
        response = self.client.post(url, {'ordering': 'up'})
        survey_url = reverse('manage:event_survey', args=(event.id,))
        self.assertRedirects(response, survey_url)
        questions = list(Question.objects.filter(survey=survey))
        eq_(questions, [question_2, question_1, question_3])

        # let's move question_1 down one
        url = reverse(
            'manage:event_survey_question_edit',
            args=(event.id, question_1.id)
        )
        response = self.client.post(url, {'ordering': 'down'})
        self.assertRedirects(response, survey_url)
        questions = list(Question.objects.filter(survey=survey))
        eq_(questions, [question_2, question_3, question_1])
