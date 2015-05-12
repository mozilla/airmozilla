import cronjobs

from airmozilla.cronlogger.decorators import capture
from . import eventemails


@cronjobs.register
@capture
def send_new_event_emails():
    eventemails.send_new_event_emails(verbose=True)
