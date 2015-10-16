from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse

from airmozilla.base.tests.testbase import DjangoTestCase
from airmozilla.surveys.models import (
    Survey,
    Question,
    Answer,
    next_question_order,
)


class TestSurvey(DjangoTestCase):

    def _create_survey(self, name='Test survey', active=True):
        survey = Survey.objects.create(name=name, active=active)
        return survey

    def test_render_questions(self):
        survey = self._create_survey()
        url = reverse('surveys:load', args=(survey.id,))
        # add a question
        question = Question.objects.create(
            survey=survey,
            question={
                'question': 'Fav color?',
                'choices': ['Red', 'Green', 'Blue']
            },
            order=next_question_order(),
        )
        # empty questions are ignored
        Question.objects.create(
            survey=survey,
            question={},
            order=next_question_order(),
        )

        # render the questions
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('type="submit"' not in response.content)

        self._login()
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('csrfmiddlewaretoken' in response.content)
        ok_('type="submit"' in response.content)

        # three choices
        eq_(response.content.count('name="%s"' % question.id), 3)
        ok_('Fav color?' in response.content)
        ok_('Red' in response.content)
        ok_('Green' in response.content)
        ok_('Blue' in response.content)

    def test_submit_response_to_questions(self):
        survey = self._create_survey()
        url = reverse('surveys:load', args=(survey.id,))
        user = self._login()

        # add a question
        question = Question.objects.create(
            survey=survey,
            question={
                'question': 'Fav color?',
                'choices': ['Red', 'Green', 'Blue']
            },
            order=next_question_order(),
        )
        Question.objects.create(
            survey=survey,
            question={
                'question': 'Gender?',
                'choices': ['Male', 'Female', 'Mixed']
            },
            order=next_question_order(),
        )
        response = self.client.post(url, {
            str(question.id): "Green",
            # note that we don't submit an answer to the second question
        })
        eq_(response.status_code, 302)
        self.assertRedirects(response, url)
        answers = Answer.objects.filter(
            question=question,
            user=user
        )
        eq_(answers.count(), 1)

    def test_submit_multiple_times(self):
        survey = self._create_survey()
        url = reverse('surveys:load', args=(survey.id,))
        user = self._login()

        # add a question
        question = Question.objects.create(
            survey=survey,
            question={
                'question': 'Fav color?',
                'choices': ['Red', 'Green', 'Blue']
            },
            order=next_question_order(),
        )
        response = self.client.post(url, {
            str(question.id): "Green",
            # note that we don't submit an answer to the second question
        })
        eq_(response.status_code, 302)
        self.assertRedirects(response, url)
        answers = Answer.objects.filter(
            question=question,
            user=user
        )
        eq_(answers.count(), 1)
        answer, = answers
        eq_(answer.answer['answer'], 'Green')

        # so far so good
        # now let's try to submit a different answer
        response = self.client.post(url, {
            str(question.id): "Red",
            # note that we don't submit an answer to the second question
        })
        eq_(response.status_code, 302)
        self.assertRedirects(response, url)
        answers = Answer.objects.filter(
            question=question,
            user=user
        )
        eq_(answers.count(), 1)
        answer, = answers
        eq_(answer.answer['answer'], 'Red')

    def test_reset_submitted_response_to_questions(self):
        survey = self._create_survey()
        url = reverse('surveys:load', args=(survey.id,))
        user = self._login()
        # add a question
        question = Question.objects.create(
            survey=survey,
            question={
                'question': 'Fav color?',
                'choices': ['Red', 'Green', 'Blue']
            },
            order=next_question_order(),
        )
        response = self.client.post(url, {
            str(question.id): "Green",
            # note that we don't submit an answer to the second question
        })
        eq_(response.status_code, 302)
        self.assertRedirects(response, url)
        answers = Answer.objects.filter(
            question=question,
            user=user
        )
        eq_(answers.count(), 1)

        response = self.client.post(url, {'resetmine': True})
        eq_(response.status_code, 302)
        answers = Answer.objects.filter(
            question=question,
            user=user
        )
        eq_(answers.count(), 0)
