from django.core.urlresolvers import reverse

from jingo import register


_STATES = [
    {
        'required': ['accepted'],
        'view': 'webrtc:summary',
        'description': 'Accepted'
    },
    {
        'required': ['submitted'],
        'view': 'webrtc:summary',
        'description': 'Submitted'
    },
    {
        'not': ['title', 'short_description', 'description'],
        'view': 'webrtc:details',
        'description': 'Details missing',
    },
    {
        'not': ['placeholder_img'],
        'view': 'webrtc:placeholder',
        'description': 'No picture',
    },
    {
        'not': ['placeholder_img'],
        'view': 'webrtc:video',
        'description': 'No picture',
    },
    {
        'not': ['upload'],
        'view': 'webrtc:video',
        'description': 'No video',
    },
]

_DEFAULT_STATE = {
    'view': 'webrtc:summary',
    'description': 'Not yet submitted',
}


def _get_state(event):
    for state in _STATES:
        if state.get('required'):
            requirements = state['required']
        else:
            requirements = state['not']
        all = True
        for requirement in requirements:
            if isinstance(requirement, basestring):
                if not getattr(event, requirement, None):
                    all = False
            else:
                if not requirement(event):
                    all = False
        if state.get('required'):
            if all:
                return state
        else:
            if not all:
                return state
    return _DEFAULT_STATE


@register.function
def webrtc_next_url(event):
    state = _get_state(event)
    assert state, event
    return reverse(state['view'], args=(event.pk,))


@register.function
def webrtc_state_description(event):
    state = _get_state(event)
    assert state, event
    return state['description']


@register.function
def webrtc_breadcrumbs(event):
    state = _get_state(event)
    links = []
    # start
    links.append({
        'url': reverse('webrtc:start'),
        'description': 'Start',
        'available': True,
    })

    # details
    links.append({
        'url': reverse('webrtc:details', args=(event.pk,)),
        'description': 'Details',
        'available': True,
    })

    available = state['view'] != 'webrtc:details'

    # placeholder
    if available:
        available = state['view'] != 'webrtc:placeholder'
    links.append({
        'url': reverse('webrtc:placeholder', args=(event.pk,)),
        'description': 'Picture',
        'available': available,
    })

    # placeholder
    if available:
        available = state['view'] != 'webrtc:video'
    links.append({
        'url': reverse('webrtc:video', args=(event.pk,)),
        'description': 'Video',
        'available': available,
    })

    # summary
    if available:
        available = state['view'] == 'webrtc:summary'
    links.append({
        'url': reverse('webrtc:summary', args=(event.pk,)),
        'description': 'Summary',
        'available': available,
    })

    return links


@register.function
def webrtc_last_available_state(event):
    return [
        each for each in webrtc_breadcrumbs(event)
        if each['available']
    ][-1]
