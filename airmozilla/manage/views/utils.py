from django.shortcuts import redirect

from jinja2 import Environment, meta

from airmozilla.base import mozillians
from airmozilla.main.models import Event, CuratedGroup
from airmozilla.main.views import is_contributor


def can_edit_event(event, user, default='manage:events'):
    if (not user.has_perm('main.change_event_others') and
            user != event.creator):
        return redirect(default)
    if event.privacy == Event.PRIVACY_COMPANY and is_contributor(user):
        return redirect(default)
    elif (
        CuratedGroup.objects.filter(event=event) and is_contributor(user)
    ):
        # Editing this event requires that you're also part of that curated
        # group.
        curated_group_names = [
            x[0] for x in
            CuratedGroup.objects.filter(event=event).values_list('name')
        ]
        any_ = any([
            mozillians.in_group(user.email, x) for x in curated_group_names
        ])
        if not any_:
            return redirect(default)


def get_var_templates(template):
    env = Environment()
    ast = env.parse(template.content)

    exceptions = (
        'vidly_tokenize',
        'edgecast_tokenize',
        'akamai_tokenize',
        'popcorn_url',
        'event',
        'poster_url',
    )
    undeclared_variables = [
        x for x in meta.find_undeclared_variables(ast)
        if x not in exceptions
    ]
    return ["%s=" % v for v in undeclared_variables]
