import cronjobs

from .tweeter import send_unsent_tweets as _send_unsent_tweets
from .pestering import pester


@cronjobs.register
def send_unsent_tweets():
    _send_unsent_tweets()


@cronjobs.register
def pester_approvals():
    pester()
