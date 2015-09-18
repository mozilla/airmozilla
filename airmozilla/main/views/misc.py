from django import http
from django.conf import settings
from django.shortcuts import redirect, render


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


def crossdomain_xml(request):
    response = http.HttpResponse(content_type='text/xml')
    response.write(
        '<?xml version="1.0"?>\n'
        '<!DOCTYPE cross-domain-policy SYSTEM '
        '"http://www.adobe.com/xml/dtds/cross-domain-policy.dtd">\n'
        '<cross-domain-policy>'
        '<allow-access-from domain="*" />'
        '</cross-domain-policy>'
    )
    response['Access-Control-Allow-Origin'] = '*'
    return response
