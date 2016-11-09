import requests

from django.conf import settings


class Auth0LookupError(Exception):
    pass


def renew_id_token(id_token):
    url = 'https://{}/delegation'.format(settings.AUTH0_DOMAIN)
    response = requests.post(url, json={
        'client_id': settings.AUTH0_CLIENT_ID,
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        'id_token': id_token,
        'api_type': 'app',
    })
    # If the response.status_code is not 200, it's still JSON but it
    # won't have a id_token.
    result = response.json()
    return result.get('id_token')
