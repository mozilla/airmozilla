from django.shortcuts import render

from airmozilla.main.models import Event


def home(request, template='main/home.html'):
    """Main view."""
    events = Event.objects.filter() # demonstration of TZ tools
    e = events[0]
    return render(request, template, {'event': e})
