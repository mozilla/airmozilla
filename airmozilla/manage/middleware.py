class CacheBustingMiddleware(object):

    def process_response(self, request, response):
        if request.path.startswith('/manage/'):
            # Tell Zeus who's the boss!
            response['Cache-Control'] = 'no-store'
        return response
