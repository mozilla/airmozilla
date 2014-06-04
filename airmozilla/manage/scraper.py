import re
from urlparse import urlparse

import readability
import requests
import pyquery

from django.conf import settings


splitter = re.compile('\s')
html = re.compile('<.*>', re.DOTALL | re.MULTILINE)
tag_content = re.compile('>(.*?)<', re.DOTALL | re.MULTILINE)


def scrape_urls(urls):
    text = []
    results = []

    for url in urls:
        url_parsed = urlparse(url)
        if not url_parsed.scheme or not url_parsed.netloc:
            continue

        if url_parsed.netloc == 'intranet.mozilla.org':
            content, status = get_content_intranet(url)
        elif url_parsed.netloc == 'etherpad.mozilla.org':
            content, status = get_content_etherpad(url)
        else:
            content, status = get_content_readability(url)

        results.append({
            'url': url,
            'status': status,
            'worked': status == 200
        })

        if content:
            text.append(content)

    return {'text': '\n'.join(text), 'results': results}


def get_urls(text):
    """given a block of text, return anything that appears to have a
    protocol (e.g https) and a domain (e.g wiki.mozilla.org)
    """
    # XXX this could be vastly improved to find URLs that start with
    # 'www' or urls that might be wrapped in a bracket.
    for token in splitter.split(text):
        url_parsed = urlparse(token)
        if not url_parsed.scheme or not url_parsed.netloc:
            continue
        yield token


def get_content_readability(url):
    key = getattr(settings, 'READABILITY_PARSER_KEY', None)
    if key:
        parser = readability.ParserClient(key)
    else:
        return None, 'No READABILITY_PARSER_KEY setting set up'
    parser_response = parser.get_article_content(url)
    status = parser_response.status
    text = []
    try:
        content = parser_response.content['content']
        for each in tag_content.findall(content):
            if each.strip():
                text.append(each.strip())

    except KeyError:
        content = None

    return '\n'.join(text), status


def get_content_intranet(url):
    for credentials, domains in settings.SCRAPE_CREDENTIALS.items():
        if 'intranet.mozilla.org' in domains:
            break
    else:
        return None, 'No credentials set up for intranet.mozilla.org'

    response = requests.get(url, auth=credentials)
    if response.status_code != 200:
        return None, response.status_code
    content = response.text
    pq = pyquery.PyQuery(content)
    text = []
    for node in pq('#mw-content-text *'):
        if node.text and node.text.strip():
            text.append(node.text.strip())
    return '\n'.join(text), response.status_code


def get_content_etherpad(url):
    url_parsed = urlparse(url)
    pad = url_parsed.path.split('/')[1]
    url = (
        'https://etherpad.mozilla.org/ep/pad/export/%s/latest?format=txt'
        % pad
    )
    response = requests.get(url)
    return response.content, response.status_code
