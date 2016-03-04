import hashlib
import re

import jinja2
from django_jinja import library

from django.template.loader import render_to_string

from airmozilla.comments.models import Comment


@library.global_function
def recurse_comments(comment, discussion,
                     request, query_filter, can_manage_comments):
    comments = Comment.objects.filter(reply_to=comment)
    comments = comments.filter(query_filter)
    context = {
        'comments': comments.order_by('created'),
        'discussion': discussion,
        'request': request,
        'Comment': Comment,
        'can_manage_comments': can_manage_comments,
        'root': False,
        'query_filter': query_filter,
    }
    return jinja2.Markup(
        render_to_string('comments/comments.html', context)
    )


@library.global_function
def gravatar_src(email, secure, size=None):
    if secure:
        tmpl = '//secure.gravatar.com/avatar/%s'
    else:
        tmpl = '//www.gravatar.com/avatar/%s'
    url = tmpl % hashlib.md5(email.lower()).hexdigest()
    url += '?d=identicon'
    if size is not None:
        url += '&s=%s' % size

    return url


@library.global_function
def obscure_email(email):
    return re.sub('(\w{3})@(\w{3})', '...@...', email)
