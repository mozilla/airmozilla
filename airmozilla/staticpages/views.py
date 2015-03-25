# Quite blatantly copied from django.contrib.flatpages.middleware

from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404, render
from django.template import loader, RequestContext
from django.utils.safestring import mark_safe

from airmozilla.main.models import Event
from .models import StaticPage


DEFAULT_TEMPLATE = 'staticpages/default.html'


def staticpage(request, url):
    if not url.startswith('/'):
        url = '/' + url
    try:
        f = get_object_or_404(StaticPage, url__exact=url)
    except Http404:
        if not url.endswith('/') and settings.APPEND_SLASH:
            url += '/'
            f = get_object_or_404(StaticPage, url__exact=url)
            return HttpResponsePermanentRedirect('%s/' % request.path)
        else:
            raise
    return render_staticpage(request, f)


def render_staticpage(request, staticpage):
    if not can_view_staticpage(staticpage, request.user):
        # We might need to kick you out if you're not allowed to see this.
        response = render(
            request,
            'staticpages/insufficient_privileges.html', {
                'staticpage': staticpage,
            },
            status=403,
        )
        return response

    if staticpage.template_name:
        t = loader.select_template(
            (staticpage.template_name, DEFAULT_TEMPLATE)
        )
    else:
        t = loader.get_template(DEFAULT_TEMPLATE)

    # To avoid having to always use the "|safe" filter in flatpage templates,
    # mark the title and content as already safe (since they are raw HTML
    # content in the first place).
    staticpage.title = mark_safe(staticpage.title)
    staticpage.content = mark_safe(staticpage.content)

    c = RequestContext(request, {
        'staticpage': staticpage,
    })
    response = HttpResponse(t.render(c))
    return response


def can_view_staticpage(page, user):
    if page.privacy == Event.PRIVACY_PUBLIC:
        return True

    if not user.is_active:
        return False

    from airmozilla.main.views import is_contributor
    if page.privacy == Event.PRIVACY_COMPANY:
        if is_contributor(user):
            return False

    return True
