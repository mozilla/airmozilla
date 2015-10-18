import json

from nose.tools import eq_, ok_

from django.core.urlresolvers import reverse

from airmozilla.main.models import Event
from airmozilla.surveys.models import Survey, Question, next_question_order
from .base import ManageTestCase


class TestCase(ManageTestCase):

    def test_event_survey(self):
        survey = Survey.objects.create(
            name='My Survey',
            active=True
        )
        Question.objects.create(
            survey=survey,
            question={},
            order=next_question_order(),

        )
        other_survey = Survey.objects.create(
            name='Other Survey',
            active=False
        )
        Question.objects.create(
            survey=other_survey,
            question={"question": "Something?"},
            order=next_question_order(),
        )
        Question.objects.create(
            survey=other_survey,
            question={"question": "Something else?"},
            order=next_question_order(),
        )

        event = Event.objects.get(title='Test event')
        event_edit_url = reverse('manage:event_edit', args=(event.id,))
        response = self.client.get(event_edit_url)
        eq_(response.status_code, 200)
        url = reverse('manage:event_survey', args=(event.id,))
        ok_(url in response.content)

        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('My Survey' in response.content)
        ok_('1 question' in response.content)
        ok_('Other Survey' in response.content)
        ok_('2 questions' in response.content)
        ok_('none' in response.content)

        eq_(Survey.events.through.objects.filter(event=event).count(), 0)

        response = self.client.post(url, {'survey': survey.id})
        eq_(response.status_code, 302)
        self.assertRedirects(response, event_edit_url)

        eq_(Survey.events.through.objects.filter(event=event).count(), 1)
        response = self.client.get(url)
        eq_(response.status_code, 200)

        # change it back to none
        response = self.client.post(url, {'survey': 0})
        eq_(response.status_code, 302)
        self.assertRedirects(response, event_edit_url)
        eq_(Survey.events.through.objects.filter(event=event).count(), 0)

    def test_list_surveys(self):
        survey = Survey.objects.create(
            name='My Survey',
            active=True
        )
        for i in range(3):
            Question.objects.create(
                survey=survey,
                question={},
                order=next_question_order(),
            )
        event = Event.objects.get(title='Test event')
        survey.events.add(event)

        url = reverse('manage:surveys')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('My Survey' in response.content)
        ok_('>3</td>' in response.content)
        ok_('>1</td>' in response.content)
        ok_("Yes, it's active" in response.content)

    def test_event_edit_link_to_surveys(self):
        event = Event.objects.get(title='Test event')
        url = reverse('manage:event_edit', args=(event.pk,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        url = reverse('manage:surveys')
        ok_(url in response.content)

        # click that button
        response = self.client.get(url)
        eq_(response.status_code, 200)

    def test_create_survey(self):
        url = reverse('manage:survey_new')
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('name="name"' in response.content)

        response = self.client.post(url, {
            'name': 'Name',
            'active': True
        })
        eq_(response.status_code, 302)
        survey = Survey.objects.get(name='Name')
        self.assertRedirects(
            response,
            reverse('manage:survey_edit', args=(survey.id,))
        )

    def test_edit_survey(self):
        survey = Survey.objects.create(name='Name')
        url = reverse('manage:survey_edit', args=(survey.id,))
        response = self.client.get(url)
        eq_(response.status_code, 200)
        ok_('value="Name"' in response.content)
        # check for error trying to activate with no questions
        response = self.client.post(url, {
            'active': True
        })
        eq_(response.status_code, 200)
        ok_("Survey must have at least one question in order to be active"
            in response.content
            )
        # add a question and check for successful activation
        Question.objects.create(
            survey=survey,
            question={},
            order=next_question_order(),
        )
        response = self.client.post(url, {
            'name': 'New Name',
            'active': True
        })
        eq_(response.status_code, 302)
        self.assertRedirects(
            response,
            reverse('manage:surveys')
        )
        survey = Survey.objects.get(id=survey.id)
        eq_(survey.name, 'New Name')
        ok_(survey.active)

    def test_delete_survey(self):
        survey = Survey.objects.create(name='Name')
        url = reverse('manage:survey_delete', args=(survey.id,))
        response = self.client.get(url)
        eq_(response.status_code, 405)

        response = self.client.post(url)
        eq_(response.status_code, 302)
        ok_(not Survey.objects.all())

    def test_create_and_delete_question(self):
        survey = Survey.objects.create(name='Name')
        url = reverse(
            'manage:survey_question_new', args=(survey.id,)
        )

        response = self.client.post(url, {})
        eq_(response.status_code, 302)
        question = Question.objects.get(survey=survey)
        url = reverse(
            'manage:survey_question_delete',
            args=(survey.id, question.id)
        )
        response = self.client.post(url)
        eq_(response.status_code, 302)
        ok_(not Question.objects.filter(survey=survey))

    def test_edit_question(self):
        survey = Survey.objects.create(name='Name')
        question = Question.objects.create(
            survey=survey,
            order=next_question_order(),
        )
        url = reverse(
            'manage:survey_question_edit',
            args=(survey.id, question.id)
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

    def test_ordering_questions(self):
        survey = Survey.objects.create(name='Name')
        question_1 = Question.objects.create(
            survey=survey,
            question={'one': 1},
            order=next_question_order(),
        )
        question_2 = Question.objects.create(
            survey=survey,
            question={'two': 2},
            order=next_question_order(),
        )
        question_3 = Question.objects.create(
            survey=survey,
            question={'three': 3},
            order=next_question_order(),
        )
        questions = list(Question.objects.filter(survey=survey))
        eq_(questions, [question_1, question_2, question_3])
        # let's move question_2 up one
        url = reverse(
            'manage:survey_question_edit',
            args=(survey.id, question_2.id)
        )
        response = self.client.post(url, {'ordering': 'up'})
        survey_questions_url = reverse(
            'manage:survey_questions',
            args=(survey.id,)
        )
        self.assertRedirects(response, survey_questions_url)
        questions = list(Question.objects.filter(survey=survey))
        eq_(questions, [question_2, question_1, question_3])

        # let's move question_1 down one
        url = reverse(
            'manage:survey_question_edit',
            args=(survey.id, question_1.id)
        )
        response = self.client.post(url, {'ordering': 'down'})
        self.assertRedirects(response, survey_questions_url)
        questions = list(Question.objects.filter(survey=survey))
        eq_(questions, [question_2, question_3, question_1])
