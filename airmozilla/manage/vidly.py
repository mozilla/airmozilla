import hashlib
import os
import tempfile
import httplib
import urllib
import urllib2
import logging
import xml.dom.minidom

from django.conf import settings


def query(tags, use_cache=False):
    template = """
    <?xml version="1.0"?>
    <Query>
        <Action>GetStatus</Action>
        <UserID>%(user_id)s</UserID>
        <UserKey>%(user_key)s</UserKey>
        %(media_links)s
    </Query>
    """
    if isinstance(tags, basestring):
        tags = [tags]

    media_links = [
        '<MediaShortLink>%s</MediaShortLink>' % x
        for x in tags
    ]

    xml_string = template % {
        'user_id': settings.VIDLY_USER_ID,
        'user_key': settings.VIDLY_USER_KEY,
        #'tag': tag,
        'media_links': '\n'.join(media_links),
    }

    response_content = _download(xml_string, use_cache=use_cache)
    dom = xml.dom.minidom.parseString(response_content)
    #print dom.toprettyxml()
    results = _unpack_dom(dom, "Task")
    return results


def medialist(status, use_cache=False):
    template = """
    <?xml version="1.0"?>
    <Query>
        <Action>GetMediaList</Action>
        <UserID>%(user_id)s</UserID>
        <UserKey>%(user_key)s</UserKey>
        <Status>%(status)s</Status>
    </Query>
    """

    xml_string = template % {
        'user_id': settings.VIDLY_USER_ID,
        'user_key': settings.VIDLY_USER_KEY,
        'status': status,
    }

    response_content = _download(xml_string, use_cache=use_cache)
    dom = xml.dom.minidom.parseString(response_content)
    #print dom.toprettyxml()
    results = _unpack_dom(dom, "Media")
    return results


def _download(xml_string, use_cache=False):
    cache_key = hashlib.md5(xml_string).hexdigest()
    cache_dir = os.path.join(
        tempfile.gettempdir(),
        'vidlydownloads',
    )
    cache_filename = os.path.join(cache_dir, '%s.xml' % cache_key)

    if use_cache and os.path.isfile(cache_filename):
        response_content = open(cache_filename).read()
    else:
        req = urllib2.Request(
            settings.VIDLY_API_URL,
            urllib.urlencode({'xml': xml_string.strip()})
        )
        try:
            response = urllib2.urlopen(req)
        except (urllib2.URLError, httplib.BadStatusLine):
            logging.error('Error on opening request', exc_info=True)
            raise
            #raise VidlyTokenizeError(
            #    'Temporary network error when trying to fetch Vid.ly token'
            #)
        response_content = response.read().strip()

        if use_cache:
            if not os.path.isdir(cache_dir):
                os.mkdir(cache_dir)
            with open(cache_filename, 'w') as f:
                f.write(response_content)

    return response_content


def _unpack_dom(dom, main_tag_name):
    def _get_text(nodelist):
        rc = []
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc.append(node.data)
        return ''.join(rc)

    tasks = dom.getElementsByTagName(main_tag_name)
    results = {}
    for task in tasks:
        item = {}
        for element in task.childNodes:
            #print repr(element)
            item[element.tagName] = _get_text(element.childNodes)
        results[item['MediaShortLink']] = item
    return results
