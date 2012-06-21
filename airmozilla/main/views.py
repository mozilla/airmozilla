from django.shortcuts import render


def home(request, template='main/home.html'):
    """Main view."""
    return render(request, template)
