import requests

from django.conf import settings


class Auth0LookupError(Exception):
    pass


# class Auth0UnauthenticatedError(Exception):
#     pass


# def get_id_token(refresh_token):
#     url = 'https://{}/delegation'.format(settings.AUTH0_DOMAIN)
#     response = requests.post(url, json={
#         'client_id': settings.AUTH0_CLIENT_ID,
#         'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
#         'refresh_token': refresh_token,
#         'api_type': 'app',
#     })
#     if response.status_code == 401:
#         return None, response.json()
#
#     if response.status_code != 200:
#         raise Auth0LookupError('{} {}'.format(
#             response.status_code,
#             response.content
#         ))
#
#     result = response.json()
#     if result.get('id_token'):
#         assert result.get('expires_in'), result
#         return result['id_token'], None
#     else:
#         # XXX Does this ever happen?!
#         return None, 'id_token not there'


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


# def validate_id_token(id_token):
#     url = 'https://{}/tokeninfo'.format(settings.AUTH0_DOMAIN)
#     response = requests.post(url, json={
#         'id_token': id_token,
#     })
#     if response.status_code == 401:
#         return False
#     assert response.status_code == 200, response.status_code
#     return response.json()
#     # return result.get('id_token')
