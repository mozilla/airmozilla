import datetime

from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings

from airmozilla.main.models import Event
from airmozilla.manage import related  # tongue twister
from airmozilla.manage import forms
from .decorators import superuser_required


@superuser_required
def related_content(request):
    es = related.get_connection()
    index = related.get_index()

    if request.method == 'POST':
        form = forms.ReindexRelatedContentForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['delete_and_recreate']:
                related.delete(es)
                related.create(es)
                form.cleaned_data['all'] = True

            since = None
            if form.cleaned_data['since']:
                since = datetime.timedelta(
                    minutes=form.cleaned_data['since']
                )
            related.index(
                all=form.cleaned_data['all'],
                since=since
            )
            messages.success(
                request,
                'Re-indexing issued.'
            )
            return redirect('manage:related_content')

    else:
        initial = {
            'since': 30,
        }
        form = forms.ReindexRelatedContentForm(initial=initial)

    query = {
        'query': {
            'match_all': {}
        }
    }
    context = {
        'form': form,
        'count_indexed': es.count(query, index=index)['count'],
        'count_events': Event.objects.scheduled_or_processing().count(),
        'index_name': index,
    }
    return render(request, 'manage/related_content.html', context)


@superuser_required
def related_content_testing(request):
    context = {
        'matches': None,
        'event': None,
    }
    if 'event' in request.GET:
        form = forms.RelatedContentTestingForm(request.GET)
        if form.is_valid():
            event = form.cleaned_data['event']
            from airmozilla.main.views import find_related_events
            context['matches'] = find_related_events(
                event,
                request.user,
                boost_title=form.cleaned_data['boost_title'],
                boost_tags=form.cleaned_data['boost_tags'],
            )
            context['event'] = event

    else:
        form = forms.RelatedContentTestingForm(initial={
            'boost_title': settings.RELATED_CONTENT_BOOST_TITLE,
            'boost_tags': settings.RELATED_CONTENT_BOOST_TAGS,
        })

    context['form'] = form
    return render(request, 'manage/related_content_testing.html', context)
