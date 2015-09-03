import datetime
# import urllib2
# from urlparse import urlparse

from django import http
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.conf import settings
# from django.core.files import File
from django.utils import timezone
# from django.core.files.temp import NamedTemporaryFile
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.functional import wraps

from jsonview.decorators import json_view
from slugify import slugify
from funfactory.urlresolvers import reverse

# from airmozilla.base.mozillians import fetch_user
from airmozilla.main.models import (
    Channel,
    Event,
    VidlySubmission,
    Template
)
from airmozilla.manage import vidly
from . import forms


def must_be_your_event(f):

    @wraps(f)
    def inner(request, id, **kwargs):
        assert request.user.is_authenticated()
        event = get_object_or_404(Event, pk=id)
        if event.creator != request.user:
            return http.HttpResponseForbidden("Not your event")
        return f(request, event, **kwargs)

    return inner


@transaction.atomic
@login_required
def start(request):
    context = {}
    if request.method == 'POST':
        form = forms.StartForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            # information = fetch_user(name, is_username='@' not in name)

            # print "INFORMATION"
            # from pprint import pprint
            # pprint( information)
            # assert information  # must have something
            # description = []
            # if information.get('bio'):
            #     description.append(information['bio'])
            # if information.get('city'):
            #     description.append('City: %s' % information['city'])
            # if information.get('ircname'):
            #     description.append('IRC nick: %s' % information['ircname'])
            # # lastly make it a string
            # description = '\n'.join(description)

            # additional_links = []
            # if information.get('url'):
            #     additional_links.append(information['url'])
            # for each in information.get('accounts', []):
            #     if '://' in each.get('identifier', ''):
            #         additional_links.append(each['identifier'])
            # # lastly make it a string
            # additional_links = '\n'.join(additional_links)

            now = timezone.now()
            slug = slug_start = slugify(name).lower()
            increment = 1
            while Event.objects.filter(slug=slug):
                slug = slug_start + '-' + timezone.now().strftime('%Y%m%d')
                if increment > 1:
                    slug += '-%s' % increment
                increment += 1

            title = name
            event = Event.objects.create(
                status=Event.STATUS_INITIATED,
                creator=request.user,
                mozillian=name,
                slug=slug,
                title=title,
                privacy=Event.PRIVACY_COMPANY,
                short_description='',
                # description=description,
                # additional_links=additional_links,
                start_time=now,
            )
            # if information.get('photo'):
            #     # download it locally and
        #     photo_name = urlparse(information['photo']).path.split('/')[-1]
            #     img_temp = NamedTemporaryFile(delete=True)
            #     img_temp.write(urllib2.urlopen(information['photo']).read())
            #     img_temp.flush()
            #     event.placeholder_img.save(
            #         photo_name,
            #         File(img_temp),
            #         save=True
            #     )
            # mozillians_channel, __ = Channel.objects.get_or_create(
            #     name=settings.MOZILLIANS_CHANNEL_NAME,
            #     slug=settings.MOZILLIANS_CHANNEL_SLUG,
            # )
            # event.channels.add(mozillians_channel)
            channel, __ = Channel.objects.get_or_create(
                name="MozShortz",
                slug="mozshortz",
            )
            event.channels.add(channel)
            # messages.info(
            #     request,
            #     "That's great!"
            # )
            return redirect('webrtc:details', event.id)
    else:
        form = forms.StartForm()
        qs = (
            Event.objects
            .filter(mozillian__isnull=False)
            .filter(creator=request.user)
        )
        for event in qs:
            context['event'] = event
    context['form'] = form
    return render(request, 'webrtc/start.html', context)


@login_required
@transaction.atomic
@must_be_your_event
def details(request, event):
    if request.method == 'POST':
        form = forms.DetailsForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            return redirect('webrtc:placeholder', event.id)
    else:
        form = forms.DetailsForm(instance=event)
    context = {
        'form': form,
        'event': event,
    }
    return render(request, 'webrtc/details.html', context)


@login_required
@transaction.atomic
@must_be_your_event
def placeholder(request, event):
    if request.method == 'POST':
        form = forms.PlaceholderForm(
            request.POST,
            request.FILES,
            instance=event
        )
        if form.is_valid():
            event = form.save()
            return redirect('webrtc:video', event.id)
    else:
        form = forms.PlaceholderForm()

    context = {'form': form, 'event': event}
    return render(request, 'webrtc/placeholder.html', context)


@login_required
@transaction.atomic
@must_be_your_event
@json_view
def photobooth(request, event):
    if request.method == 'POST':
        form = forms.PlaceholderForm(
            request.POST,
            request.FILES,
            instance=event
        )
        if form.is_valid():
            event = form.save()
            return {'url': reverse('webrtc:video', args=(event.id,))}
    else:
        form = forms.PlaceholderForm()

    context = {'form': form, 'event': event}
    return render(request, 'webrtc/photobooth.html', context)


@login_required
@transaction.atomic
@must_be_your_event
def video(request, event):
    context = {'event': event}
    request.session['active_event'] = event.id
    return render(request, 'webrtc/video.html', context)


@login_required
@transaction.atomic
@must_be_your_event
def summary(request, event):
    if request.method == 'POST':
        # Start the archiving process.
        # This is basically the same code as
        # in manage.views.vidly_url_to_shortcode().
        token_protection = event.privacy != Event.PRIVACY_PUBLIC
        # email = request.user.email
        email = settings.EMAIL_FROM_ADDRESS
        url = event.upload.url
        shortcode, error = vidly.add_media(
            url,
            email=email,
            token_protection=token_protection,
            hd=True,
        )
        VidlySubmission.objects.create(
            event=event,
            url=url,
            email=email,
            token_protection=token_protection,
            hd=True,
            tag=shortcode,
            submission_error=error
        )
        event.archive_time = None
        event.status = Event.STATUS_PENDING
        template = Template.objects.get(default_archive_template=True)
        event.template = template
        event.template_environment = {'tag': shortcode}
        event.save()
        messages.info(
            request,
            "Excellent! Your video is being transcoded. "
            "Once it finishes, you'll receive an email."
        )
        return redirect('webrtc:summary', event.id)

    successful_vidly_submission = False
    # If the uploaded file has a successful VidlySubmission, there's nothing
    # the user needs to do at this point.
    if event.upload:
        submissions = VidlySubmission.objects.filter(
            event=event,
            url=event.upload.url,
            submission_error__isnull=True,
        )
        for submission in submissions.order_by('-submission_time'):
            successful_vidly_submission = True
            break

    context = {
        'event': event,
        'successful_vidly_submission': successful_vidly_submission,
    }
    return render(request, 'webrtc/summary.html', context)


@json_view
def save(request):
    for key in request.FILES:
        file = request.FILES[key]
        filename = datetime.datetime.now().strftime('file-%H%S.webm')
        with open('/Users/peterbe/Downloads/' + filename, 'wb') as f:
            f.write(file.read())

    return {'done': 'OK'}
