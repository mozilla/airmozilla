import functools
import warnings

from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import Permission
from django.shortcuts import redirect
from django.core.urlresolvers import reverse


staff_required = user_passes_test(lambda u: u.is_staff)
superuser_required = user_passes_test(lambda u: u.is_superuser)


def permission_required(perm):
    if settings.DEBUG:  # pragma: no cover
        ct, codename = perm.split('.', 1)
        if not Permission.objects.filter(
            content_type__app_label=ct,
            codename=codename
        ):
            warnings.warn(
                "No known permission called %r" % perm,
                UserWarning,
                2
            )

    def inner_render(fn):
        @functools.wraps(fn)
        def wrapped(request, *args, **kwargs):
            # if you're not even authenticated, redirect to /login
            if not request.user.has_perm(perm):
                request.session['failed_permission'] = perm
                return redirect(reverse('manage:insufficient_permissions'))
            return fn(request, *args, **kwargs)
        return wrapped
    return inner_render


def cancel_redirect(redirect_view):
    """Redirect wrapper for POST requests which contain a cancel field."""
    def inner_render(fn):
        @functools.wraps(fn)
        def wrapped(request, *args, **kwargs):
            if request.method == 'POST' and 'cancel' in request.POST:
                if callable(redirect_view):
                    url = redirect_view(request, *args, **kwargs)
                else:
                    url = reverse(redirect_view)
                return redirect(url)
            return fn(request, *args, **kwargs)
        return wrapped
    return inner_render
