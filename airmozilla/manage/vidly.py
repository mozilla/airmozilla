import httplib
import urllib
import urllib2
import logging
import xml.dom.minidom
import xml.etree.ElementTree as ET

import requests

from django.core.cache import cache
from django.conf import settings


class VidlyTokenizeError(Exception):
    pass


class VidlyStatisticsError(Exception):
    pass


class VidlyUpdateError(Exception):
    pass


class VidlyNotFoundError(Exception):
    pass


def tokenize(tag, seconds):
    cache_key = 'vidly_tokenize:%s' % tag
    token = cache.get(cache_key)
    if token is not None:
        return token

    query = """
    <?xml version="1.0"?>
    <Query>
        <Action>GetSecurityToken</Action>
        <UserID>%(user_id)s</UserID>
        <UserKey>%(user_key)s</UserKey>
        <MediaShortLink>%(tag)s</MediaShortLink>
        <ExpirationTimeSeconds>%(seconds)s</ExpirationTimeSeconds>
    </Query>
    """
    xml_string = query % {
        'user_id': settings.VIDLY_USER_ID,
        'user_key': settings.VIDLY_USER_KEY,
        'tag': tag,
        'seconds': seconds,
    }

    req = urllib2.Request(
        settings.VIDLY_API_URL,
        urllib.urlencode({'xml': xml_string.strip()})
    )
    try:
        response = urllib2.urlopen(req)
    except (urllib2.URLError, httplib.BadStatusLine):
        logging.error('Error on opening request', exc_info=True)
        raise VidlyTokenizeError(
            'Temporary network error when trying to fetch Vid.ly token'
        )
    response_content = response.read().strip()
    root = ET.fromstring(response_content)

    success = root.find('Success')
    token = None
    error_code = None
    if success is not None:
        token = success.find('Token').text
    else:
        errors = root.find('Errors')
        if errors is not None:
            error = errors.find('Error')
            error_code = error.find('ErrorCode').text

    if error_code == '8.1':
        # if you get a 8.1 error code it means you tried to get a
        # security token for a vid.ly video that doesn't need to be
        # secure.
        cache.set(cache_key, '', 60 * 60 * 24)
        return ''

    if token:
        # save it for a very short time.
        # it's safer and at least protects us from possible excessive hits
        # over the network.
        cache.set(cache_key, token, 60)
    else:
        logging.error('Unable fetch token for tag %r' % tag)
        logging.info(response_content)

    return token


def add_media(
    url, email=None, token_protection=None, hd=False, notify_url=None
):
    root = ET.Element('Query')
    ET.SubElement(root, 'Action').text = 'AddMediaLite'
    ET.SubElement(root, 'UserID').text = settings.VIDLY_USER_ID
    ET.SubElement(root, 'UserKey').text = settings.VIDLY_USER_KEY
    if notify_url and email:
        raise TypeError("Can't have both notify_url and email")
    if notify_url:
        ET.SubElement(root, 'Notify').text = notify_url
    elif email:
        ET.SubElement(root, 'Notify').text = email
    source = ET.SubElement(root, 'Source')
    ET.SubElement(source, 'SourceFile').text = url
    ET.SubElement(source, 'HD').text = hd and 'YES' or 'NO'
    ET.SubElement(source, 'CDN').text = 'AWS'
    if token_protection:
        protect = ET.SubElement(source, 'Protect')
        ET.SubElement(protect, 'Token')

    xml_string = ET.tostring(root)
    req = urllib2.Request(
        settings.VIDLY_API_URL,
        urllib.urlencode({'xml': xml_string.strip()})
    )
    response = urllib2.urlopen(req)
    response_content = response.read().strip()
    root = ET.fromstring(response_content)
    success = root.find('Success')
    if success is not None:
        # great!
        return success.find('MediaShortLink').find('ShortLink').text, None
    logging.error(response_content)
    # error!
    return None, response_content


def query(shortcodes):
    template = """
    <?xml version="1.0"?>
    <Query>
        <Action>GetStatus</Action>
        <UserID>%(user_id)s</UserID>
        <UserKey>%(user_key)s</UserKey>
        %(media_links)s
    </Query>
    """
    if isinstance(shortcodes, basestring):
        shortcodes = [shortcodes]

    media_links = [
        '<MediaShortLink>%s</MediaShortLink>' % x
        for x in shortcodes
    ]

    xml_string = template % {
        'user_id': settings.VIDLY_USER_ID,
        'user_key': settings.VIDLY_USER_KEY,
        # 'tag': tag,
        'media_links': '\n'.join(media_links),
    }

    response_content = _download(xml_string)
    dom = xml.dom.minidom.parseString(response_content)
    results = _unpack_dom(dom, "Task")
    return results


def medialist(status):
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

    response_content = _download(xml_string)
    dom = xml.dom.minidom.parseString(response_content)
    results = _unpack_dom(dom, "Media")
    return results


def delete_media(shortcode, email=None):
    root = ET.Element('Query')
    ET.SubElement(root, 'Action').text = 'DeleteMedia'
    ET.SubElement(root, 'UserID').text = settings.VIDLY_USER_ID
    ET.SubElement(root, 'UserKey').text = settings.VIDLY_USER_KEY
    if email:
        ET.SubElement(root, 'Notify').text = email
    ET.SubElement(root, 'MediaShortLink').text = shortcode
    xml_string = ET.tostring(root)
    req = urllib2.Request(
        settings.VIDLY_API_URL,
        urllib.urlencode({'xml': xml_string.strip()})
    )
    response = urllib2.urlopen(req)
    response_content = response.read().strip()
    root = ET.fromstring(response_content)
    success = root.find('Success')
    if success is not None:
        # great!
        return success.find('MediaShortLink').text, None
    logging.error(response_content)
    # error!
    return None, response_content


def statistics(shortcode):
    assert shortcode
    root = ET.Element('Query')
    ET.SubElement(root, 'Action').text = 'GetStatistics'
    ET.SubElement(root, 'UserID').text = settings.VIDLY_USER_ID
    ET.SubElement(root, 'UserKey').text = settings.VIDLY_USER_KEY
    filter = ET.SubElement(root, 'Filter')
    ET.SubElement(filter, 'MediaShortLink').text = shortcode
    xml_string = ET.tostring(root)
    response_content = _download(xml_string)
    root = ET.fromstring(response_content)
    success = root.find('Success')
    if success is None:
        raise VidlyStatisticsError(response_content)
    stats_info = success.find('StatsInfo')
    total_hits = stats_info.find('TotalHits')
    if total_hits is not None:
        # great!
        return {'total_hits': int(total_hits.text)}
    logging.error(response_content)


def update_media_protection(shortcode, protect, notify_url=None):
    """
    <?xml version="1.0"?>
    <Query>
        <Action>UpdateMedia</Action>
        <userid>[userid]</userid>
        <userkey>[userkey]</userkey>
        <Notify>[URL_or_email]</Notify>
        <Source>
            <MediaShortLink>[shortlink]</MediaShortLink>
            <Protect>
            </Protect>
        </Source>
    </Query>
    """
    assert shortcode
    root = ET.Element('Query')
    ET.SubElement(root, 'Action').text = 'UpdateMedia'
    ET.SubElement(root, 'UserID').text = settings.VIDLY_USER_ID
    ET.SubElement(root, 'UserKey').text = settings.VIDLY_USER_KEY
    if notify_url:
        ET.SubElement(root, 'Notify').text = notify_url
    source = ET.SubElement(root, 'Source')
    ET.SubElement(source, 'MediaShortLink').text = shortcode
    if protect:
        node = ET.SubElement(source, 'Protect')
        ET.SubElement(node, 'Token')
    else:
        ET.SubElement(source, 'Protect').text = ""
    xml_string = ET.tostring(root)
    response_content = _download(xml_string)
    root = ET.fromstring(response_content)
    errors = root.find('Errors')
    if errors is not None:
        # For example...
        """
        <?xml version="1.0"?>
        <Response>
            <Message>Action failed: none of media short link w...</Message>
            <MessageCode>2.6</MessageCode>
            <Errors>
                <Error>
                    <ErrorCode>8.4</ErrorCode>
                    <ErrorName>Media invalidation in progress</ErrorName>
                    <Description>Media invalidation in progress</Description>
                    <Suggestion></Suggestion>
                    <SourceFile>8q8e5h</SourceFile>
                </Error>
            </Errors>
        </Response>
        """
        error = errors.find('Error')
        error_code = error.find('ErrorCode').text
        error_name = error.find('ErrorName').text
        raise VidlyUpdateError(
            "%s: %s" % (
                error_code,
                error_name,
            )
        )


def get_results_from_xml(xml_string):
    dom = xml.dom.minidom.parseString(xml_string)
    results = _unpack_dom(dom, "Result")
    return results


def _download(xml_string):
    req = urllib2.Request(
        settings.VIDLY_API_URL,
        urllib.urlencode({'xml': xml_string.encode('utf8').strip()})
    )
    try:
        response = urllib2.urlopen(req)
    except (urllib2.URLError, httplib.BadStatusLine):
        logging.error('Error on opening request', exc_info=True)
        raise
        # raise VidlyTokenizeError(
        #     'Temporary network error when trying to fetch Vid.ly token'
        # )
    response_content = response.read().strip()

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
            item[element.tagName] = _get_text(element.childNodes)
        results[item['MediaShortLink']] = item
    return results


def get_video_redirect_info(tag, format_, hd=False):
    assert format_ in ('webm', 'mp4'), format_
    if hd:
        format_ = 'hd_{}'.format(format_)
    vidly_url = 'https://vid.ly/{}?content=video&format={}'.format(
        tag,
        format_
    )
    req = requests.head(vidly_url)
    if req.status_code == 404:
        raise VidlyNotFoundError(tag)
    assert req.status_code == 302, (req.status_code, vidly_url)
    req2 = requests.head(req.headers['Location'])
    data = {
        'url': req.headers['Location'].split('?t=')[0],
        'length': int(req2.headers['Content-Length']),
        'type': req2.headers['Content-Type'],
    }
    return data
