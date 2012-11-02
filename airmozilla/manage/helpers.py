import textwrap
from jingo import register
from django.template import Context
from django.template.loader import get_template


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
