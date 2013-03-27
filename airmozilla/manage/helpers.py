import cgi
import urllib
import textwrap
from jingo import register
from django.template import Context
from django.template.loader import get_template
from airmozilla.main.models import Event, EventOldSlug


@register.function
def bootstrapform(form):
    template = get_template("bootstrapform/form.html")
    context = Context({'form': form})
    return template.render(context)


@register.function
def invalid_form(form):
    """return true if the form is bound and invalid"""
    return form.is_bound and not form.is_valid()


@register.function
def line_indent(text, indent=' ' * 4):
    return '\n'.join(textwrap.wrap(text,
                                   initial_indent=indent,
                                   subsequent_indent=indent))


@register.function
def count_events_with_tag(tag):
    return Event.objects.filter(tags=tag).count()


@register.function
def query_string(request, **kwargs):
    current = request.META.get('QUERY_STRING')
    parsed = cgi.parse_qs(current)
    parsed.update(kwargs)
    return urllib.urlencode(parsed, True)


@register.function
def clashes_with_event(url):
    """used for URLs belonging to Flatpages to see if their
    URL is possibly clashing with an event.
    """
    possible = url.split('/', 2)[1]
    try:
        return Event.objects.get(slug=possible)
    except Event.DoesNotExist:
        try:
            return EventOldSlug.objects.get(slug=possible).event
        except EventOldSlug.DoesNotExist:
            return False
