from django.shortcuts import redirect

from jinja2 import Environment, meta

from airmozilla.base import mozillians
from airmozilla.main.models import Event, CuratedGroup
from airmozilla.main.views import is_contributor


STOPWORDS = (
    "a able about across after all almost also am among an and "
    "any are as at be because been but by can cannot could dear "
    "did do does either else ever every for from get got had has "
    "have he her hers him his how however i if in into is it its "
    "just least let like likely may me might most must my "
    "neither no nor not of off often on only or other our own "
    "rather said say says she should since so some than that the "
    "their them then there these they this tis to too twas us "
    "wants was we were what when where which while who whom why "
    "will with would yet you your".split()
)


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
        if not mozillians.in_groups(
            user.email,
            curated_group_names
        ):
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
    )
    undeclared_variables = [x for x in meta.find_undeclared_variables(ast)
                            if x not in exceptions]
    return ["%s=" % v for v in undeclared_variables]
