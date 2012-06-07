import logging

from django.shortcuts import render

import commonware
from funfactory.log import log_cef


log = commonware.log.getLogger('playdoh')


def home(request, template='main/home.html'):
    """Main view."""
    return render(request, template)
