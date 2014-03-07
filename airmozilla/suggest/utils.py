import re
from urlparse import urljoin

import requests

meta_tag_regex = re.compile('<meta ([^>]+)>', re.I | re.M)
content_regex = re.compile('content=[\'""](.*)[\'""]')


def find_open_graph_image_url(url):
    response = requests.get(url)
    assert response.status_code == 200, response.status_code
    html = response.content
    for meta_tag in meta_tag_regex.findall(html):
        if 'og:image' in meta_tag:
            for meta_url in content_regex.findall(meta_tag):
                return urljoin(url, meta_url)
