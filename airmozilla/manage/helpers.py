from jingo import register
from django.template import Context
from django.template.loader import get_template


@register.function
def bootstrapform(form):
    template = get_template("bootstrapform/form.html")
    context = Context({'form': form})
    return template.render(context)
