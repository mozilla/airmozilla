import datetime

from django.shortcuts import render, redirect
from django.contrib import messages

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
    }
    return render(request, 'manage/related_content.html', context)
