import json

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.db import transaction

from jsonview.decorators import json_view

from airmozilla.main.models import Event
from airmozilla.manage import forms
from airmozilla.surveys.models import Survey, Question

from .decorators import (
    staff_required,
    permission_required,
    cancel_redirect
)


@staff_required
@permission_required('surveys.change_survey')
@transaction.commit_on_success
def surveys_(request):  # funny name to avoid clash with surveys module
    context = {
        'surveys': Survey.objects.all().order_by('-created'),
    }

    def count_events(this):
        return Survey.events.through.objects.filter(survey=this).count()

    def count_survey_questions(this):
        return Question.objects.filter(survey=this).count()

    context['count_events'] = count_events
    context['count_survey_questions'] = count_survey_questions
    return render(request, 'manage/surveys.html', context)


@staff_required
@permission_required('surveys.change_survey')
@transaction.commit_on_success
def survey_new(request):
    if request.method == 'POST':
        form = forms.SurveyNewForm(
            request.POST,
            instance=Survey()
        )
        if form.is_valid():
            survey = form.save()
            messages.success(request, 'Survey created.')
            return redirect('manage:survey_edit', survey.id)
    else:
        form = forms.SurveyNewForm()
    context = {'form': form}
    return render(request, 'manage/survey_new.html', context)


@staff_required
@permission_required('surveys.change_survey')
@cancel_redirect('manage:surveys')
@transaction.commit_on_success
def survey_edit(request, id):
    survey = get_object_or_404(Survey, id=id)
    if request.method == 'POST':
        form = forms.SurveyEditForm(request.POST, instance=survey)
        if form.is_valid():
            form.save()
            messages.info(request, 'Survey saved.')
            return redirect('manage:surveys')
    else:
        form = forms.SurveyEditForm(instance=survey)
    context = {
        'form': form,
        'survey': survey,
        'events_using': Event.objects.filter(survey=survey),
        'questions': Question.objects.filter(survey=survey),
    }
    return render(request, 'manage/survey_edit.html', context)


@require_POST
@staff_required
@permission_required('surveys.delete_survey')
@cancel_redirect('manage:surveys')
@transaction.commit_on_success
def survey_delete(request, id):
    survey = get_object_or_404(Survey, id=id)
    survey.delete()
    return redirect('manage:surveys')


@require_POST
@staff_required
@permission_required('surveys.add_question')
@transaction.commit_on_success
def survey_question_new(request, id):
    survey = get_object_or_404(Survey, id=id)
    Question.objects.create(survey=survey)
    return redirect('manage:survey_questions', survey.id)


@json_view
@require_POST
@staff_required
@permission_required('surveys.change_question')
@transaction.commit_on_success
def survey_question_edit(request, id, question_id):
    survey = get_object_or_404(Survey, id=id)
    question = get_object_or_404(Question, survey=survey, id=question_id)

    if 'question' in request.POST:
        # it must be valid JSON
        form = forms.QuestionForm(request.POST)
        if form.is_valid():
            question.question = form.cleaned_data['question']
            question.save()
        else:
            return {'error': form.errors['question']}
    elif request.POST.get('ordering') in ('up', 'down'):
        direction = request.POST.get('ordering')
        questions = list(Question.objects.filter(survey=survey))
        current = questions.index(question)
        this = questions.pop(current)
        if direction == 'up':
            questions.insert(current - 1, this)
        else:
            questions.insert(current + 1, this)

        for i, question in enumerate(questions):
            if i != question.order:
                question.order = i
                question.save()

        return redirect('manage:survey_questions', survey.id)
    else:  # pragma: no cover
        raise NotImplementedError

    return {
        'question': json.dumps(question.question, indent=2)
    }


@staff_required
@permission_required('surveys.change_survey')
@cancel_redirect('manage:surveys')
@transaction.commit_on_success
def survey_questions(request, id):
    survey = get_object_or_404(Survey, id=id)
    context = {
        'survey': survey,
        'questions': Question.objects.filter(survey=survey),
    }
    return render(request, 'manage/survey_edit_questions.html', context)


@require_POST
@staff_required
@permission_required('surveys.delete_question')
@transaction.commit_on_success
def survey_question_delete(request, id, question_id):
    survey = get_object_or_404(Survey, id=id)
    get_object_or_404(Question, survey=survey, id=question_id).delete()
    return redirect('manage:survey_questions', survey.id)
