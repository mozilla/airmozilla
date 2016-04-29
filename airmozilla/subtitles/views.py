import json

from django import http
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

from airmozilla.subtitles.models import AmaraCallback, AmaraVideo


@csrf_exempt
@require_POST
def amara_callback(request):
    try:
        post = request.body and json.loads(request.body) or {}
    except ValueError:
        return http.HttpResponseBadRequest('Invalid JSON body')
    try:
        video_id = post['video_id']
    except KeyError:
        return http.HttpResponseBadRequest('no video_id')
    try:
        api_url = post['api_url']
    except KeyError:
        return http.HttpResponseBadRequest('no api_url')

    amara_callback = AmaraCallback.objects.create(
        payload=post,
        api_url=api_url,
        video_id=video_id,
        team=post.get('team'),
        project=post.get('project'),
        language_code=post.get('language_code'),
    )
    amara_videos = AmaraVideo.objects.filter(video_id=video_id)
    for amara_video in amara_videos.order_by('-created')[:1]:
        amara_callback.amara_video = amara_video
        amara_callback.save()

    return http.HttpResponse('OK {}'.format(amara_callback.id))
