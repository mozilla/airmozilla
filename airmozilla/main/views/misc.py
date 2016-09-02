from django import http
from django.conf import settings
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required

from jsonview.decorators import json_view

from airmozilla.base import mozillians


def debugger__(request):  # pragma: no cover
    r = http.HttpResponse()
    r.write('BROWSERID_AUDIENCES=%r\n' % settings.BROWSERID_AUDIENCES)
    r.write('Todays date: 2014-05-21 14:02 PST\n')
    r.write('Request secure? %s\n' % request.is_secure())
    r['Content-Type'] = 'text/plain'
    return r


def god_mode(request):
    if not (settings.DEBUG and settings.GOD_MODE):
        raise http.Http404()

    if request.method == 'POST':
        from django.contrib.auth.models import User
        user = User.objects.get(email__iexact=request.POST['email'])
        from django.contrib import auth
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        auth.login(request, user)
        return redirect('/')

    context = {}
    return render(request, 'main/god_mode.html', context)


def edgecast_smil(request):
    context = {}
    for key, value in request.GET.items():
        context[key] = value
    response = render(request, 'main/edgecast_smil.xml', context)
    response['Content-Type'] = 'application/smil'
    response['Access-Control-Allow-Origin'] = '*'
    return response


@login_required
@json_view
def curated_groups_autocomplete(request):
    if 'q' not in request.GET:
        return http.HttpResponseBadRequest('q')
    q = request.GET.get('q', '').strip()
    if not q:
        return {'groups': []}

    all_ = mozillians.get_all_groups(name=q)
    ids = [x['id'] for x in all_]
    all_.extend([
        x for x in mozillians.get_all_groups(name_search=q)
        if x['id'] not in ids
    ])

    def describe_group(group):
        if group['member_count'] == 1:
            return '%s (1 member)' % (group['name'],)
        else:
            return (
                '%s (%s members)' % (group['name'], group['member_count'])
            )

    groups = [
        (x['name'], describe_group(x))
        for x in all_
    ]
    # naively sort by how good the match is
    groups.sort(key=lambda x: x[0].lower().find(q.lower()))
    return {'groups': groups}
