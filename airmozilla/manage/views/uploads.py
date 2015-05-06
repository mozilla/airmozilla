from django.shortcuts import render

from airmozilla.base.utils import paginate
from airmozilla.uploads.models import Upload

from .decorators import superuser_required


@superuser_required
def uploads(request):
    records = (
        Upload.objects
        .select_related('event')
        .order_by('-created')
    )
    paged = paginate(records, request.GET.get('page'), 20)
    context = {
        'paginate': paged,
    }
    return render(request, 'manage/uploads.html', context)

#
# @superuser_required
# def loggedsearches_stats(request):
#     context = {}
#
#     now = timezone.now()
#     today = now.replace(hour=0, minute=0, second=0, microsecond=0)
#     this_week = today - datetime.timedelta(days=today.weekday())
#     this_month = today.replace(day=1)
#     this_year = this_month.replace(month=1)
#
#     groups = (
#         ('All searches', {}),
#         ('Successful searches', {'results__gt': 0}),
#         ('Failed searches', {'results': 0}),
#     )
#     context['groups'] = []
#     qs_base = LoggedSearch.objects.all()
#     for group_name, filters in groups:
#         qs = qs_base.filter(**filters)
#
#         counts = {}
#         counts['today'] = qs.filter(date__gte=today).count()
#         counts['this_week'] = qs.filter(date__gte=this_week).count()
#         counts['this_month'] = qs.filter(date__gte=this_month).count()
#         counts['this_year'] = qs.filter(date__gte=this_year).count()
#         counts['ever'] = qs.count()
#         context['groups'].append((group_name, counts, False))
#
#     qs = (
#         qs_base.extra(
#             select={'term_lower': 'LOWER(term)'}
#         )
#         .values('term_lower')
#         .annotate(count=Count('term'))
#         .order_by('-count')
#     )
#     terms = {}
#     terms['today'] = qs.filter(date__gte=today)[:5]
#     terms['this_week'] = qs.filter(date__gte=this_week)[:5]
#     terms['this_month'] = qs.filter(date__gte=this_month)[:5]
#     terms['this_year'] = qs.filter(date__gte=this_year)[:5]
#     terms['ever'] = qs[:5]
#     context['groups'].append(
#         (
#             'Most common terms (case insensitive, top 5)',
#             terms,
#             True
#         )
#     )
#
#     return render(request, 'manage/loggedsearches_stats.html', context)
