from jingo import register
from django.contrib.humanize.templatetags import humanize
from django.template import Context
from django.template.loader import get_template


@register.function
def bootstrapform(form):
    template = get_template("bootstrapform/form.html")
    context = Context({'form': form})
    return template.render(context)


@register.filter
def naturaltime(time):
    return humanize.naturaltime(time)
