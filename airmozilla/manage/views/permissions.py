import warnings

from django.contrib.auth.models import Permission
from django.shortcuts import render


def insufficient_permissions(request):
    context = {}
    perm = request.session.get('failed_permission')
    if perm:
        # convert that into the actual Permission object
        ct, codename = perm.split('.', 1)
        try:
            permission = Permission.objects.get(
                content_type__app_label=ct,
                codename=codename
            )
            context['failed_permission'] = permission
        except Permission.DoesNotExist:
            warnings.warn('Unable to find permission %r' % perm)
    return render(request, 'manage/insufficient_permissions.html', context)
