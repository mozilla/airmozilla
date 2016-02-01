from django.shortcuts import render
from django.conf import settings

from .decorators import superuser_required
from airmozilla.manage import forms
from airmozilla.manage import sending


@superuser_required
def home(request):
    context = {
        'EMAIL_BACKEND': settings.EMAIL_BACKEND,
        'EMAIL_FILE_PATH': getattr(settings, 'EMAIL_FILE_PATH', None),
    }

    sent_email = None
    if request.method == 'POST':
        form = forms.EmailSendingForm(request.POST)
        if form.is_valid():
            to = form.cleaned_data['to']
            subject = form.cleaned_data['subject']
            html_body = form.cleaned_data['html_body']
            sent_email = sending.email_sending_test(
                subject,
                html_body,
                to,
                request,
            )
            sent_html_body, = [
                x[0] for x in sent_email.alternatives if x[1] == 'text/html'
            ]
            context['sent_html_body'] = sent_html_body
    else:
        initial = {
            'to': 'some@example.com',
            'subject': 'This is a Test Subject',
            'html_body': (
                "<p>Some paragraph here first.</p>\n\n"
            )
        }
        form = forms.EmailSendingForm(initial=initial)
    context['form'] = form
    context['sent_email'] = sent_email
    return render(request, 'manage/email_sending.html', context)
