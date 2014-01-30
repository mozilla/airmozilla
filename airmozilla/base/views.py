import sys

from django.shortcuts import render_to_response


_retry_exceptions = []
try:
    from psycopg2 import OperationalError
    # in Django 1.5 the OperationalErrors are going to be replaced with a
    # generic DatabaseError exception. But for now, use this.
    _retry_exceptions.append(OperationalError)
except ImportError:
    pass


def handler500(request):
    data = {}
    err_type, __, __ = sys.exc_info()
    if err_type in _retry_exceptions:
        data['retry_after'] = 10
        response = render_to_response('503.html', data)
        response['Retry-after'] = data['retry_after']
        response.status_code = 503
        return response
    # use render_to_response so none of the context processors are used
    response = render_to_response('500.html', data)
    response.status_code = 500
    return response
