from collections import defaultdict

from django.shortcuts import get_object_or_404, render, redirect
from django.db import transaction
from django import forms

from .models import Survey, Question, Answer


@transaction.commit_on_success
def load(request, id):
    survey = get_object_or_404(Survey, id=id, active=True)
    context = {'survey': survey}

    questions = Question.objects.filter(survey=survey)
    answers = Answer.objects.filter(question__in=questions)

    if request.method == 'POST' and request.POST.get('resetmine'):
        answers.filter(user=request.user).delete()
        return redirect('surveys:load', survey.id)

    show_answers = True  # default
    if request.user.is_authenticated():
        # don't show answers if this is POST
        your_answers = answers.filter(user=request.user)
        if request.method == 'POST' or not your_answers:
            show_answers = False
    else:
        your_answers = answers.none()

    if show_answers:
        # make a map of question -> [answers]
        _answers = defaultdict(list)
        for answer in answers:
            _answers[answer.question].append(answer)

        questions_dicts = []
        for question in questions:
            if not question.question:
                continue
            item = {
                'label': question.question['question'],  # ugly
                'choices': []
            }
            choices = defaultdict(int)

            total_answers = 0
            for answer in _answers[question]:
                choices[answer.answer['answer']] += 1
                total_answers += 1

            try:
                your_answer = your_answers.get(question=question)
            except Answer.DoesNotExist:
                your_answer = None

            for choice in question.question['choices']:
                try:
                    percent = 100.0 * choices[choice] / total_answers
                except ZeroDivisionError:
                    percent = 0.0
                choice_item = {
                    'number': choices[choice],
                    'percent': percent,
                    'answer': choice,
                    'your_answer': (
                        your_answer and choice == your_answer.answer['answer']
                    )
                }
                item['choices'].append(choice_item)
            questions_dicts.append(item)
        context['questions'] = questions_dicts
        context['answers'] = answers
        return render(request, 'surveys/answers.html', context)

    if request.method == 'POST':
        form = forms.Form(request.POST)
    else:
        form = forms.Form()

    for question in questions:
        if not question.question:
            # it's empty
            continue
        q = question.question
        if q.get('question') and q.get('choices'):
            field = forms.ChoiceField(q.get('question'))
            field.label = q.get('question')
            field.widget = forms.widgets.RadioSelect()
            field.choices = [
                (x, x) for x in q.get('choices')
            ]
            field.required = False
            form.fields[str(question.id)] = field

    if request.method == 'POST':
        if form.is_valid():
            # delete any previous answers
            Answer.objects.filter(
                question=question,
                user=request.user
            ).delete()
            for question_id, answer in form.cleaned_data.items():
                if not answer:
                    continue
                question = questions.get(id=question_id)
                Answer.objects.create(
                    question=question,
                    user=request.user,
                    answer={
                        'answer': answer
                    }
                )
            return redirect('surveys:load', survey.id)

    context['form'] = form
    return render(request, 'surveys/questions.html', context)
