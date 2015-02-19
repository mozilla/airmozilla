#!/usr/bin/env python

import uuid
import re
import json
from tornado import ioloop
from tornado import web
from tornado.options import define, options

define("debug", default=False, help="run in debug mode", type=bool)
define("port", default=9999, help="run on the given port", type=int)


GET_STATUS_XML = (
    '<?xml version="1.0"?>'
    '<Response><Message>Action successful.</Message>'
    '<MessageCode>4.1</MessageCode><Success><Task><UserID>1234</UserID>'
    '<MediaShortLink>%(tag)s</MediaShortLink>'
    '<SourceFile>http://videos.mozilla.org/bla.f4v</SourceFile>'
    '<BatchID>35402</BatchID>'
    '<Status>%(status)s</Status>'
    '<Private>false</Private>'
    '<PrivateCDN>false</PrivateCDN><Created>2012-08-23 19:30:58</Created>'
    '<Updated>2012-08-23 20:44:22</Updated>'
    '<UserEmail>airmozilla@mozilla.com</UserEmail>'
    '</Task></Success></Response>'
)

SAMPLE_MEDIALIST_XML = (
    '<?xml version="1.0"?>'
    '<Response><Message>OK</Message><MessageCode>7.4</MessageCode><Success>'
    '%(media)s'
    '</Success></Response>'
)

_SAMPLE_MEDIALIST_MEDIA_XML = (
    '<Media><MediaShortLink>%(tag)s</MediaShortLink><VanityLink/>'
    '<Notify>vvm@spb-team.com</Notify><Created>2011-12-25 18:45:56</Created>'
    '<Updated>2012-11-28 14:05:07</Updated><Status>%(status)s</Status>'
    '<IsDeleted>false</IsDeleted><IsPrivate>false</IsPrivate>'
    '<IsPrivateCDN>false</IsPrivateCDN><CDN>AWS</CDN></Media>'
)

_SAMPLE_ADD_MEDIA_XML = (
    '<?xml version="1.0"?>'
    '<Response>'
    '<Message>All medias have been added.</Message>'
    '<MessageCode>2.1</MessageCode>'
    '<BatchID>47520</BatchID>'
    '<Success>'
    '<MediaShortLink>'
    '<SourceFile>http://www.com/file.flv</SourceFile>'
    '<ShortLink>%(shortcode)s</ShortLink>'
    '<MediaID>13969839</MediaID>'
    '<QRCode>http://vid.ly/8oxv6x/qrcodeimg</QRCode>'
    '<HtmlEmbed>code code</HtmlEmbed>'
    '<EmailEmbed>more code code</EmailEmbed>'
    '</MediaShortLink>'
    '</Success>'
    '</Response>'
)

_SAMPLE_ADD_MEDIA_ERROR_XML = (
    '<?xml version="1.0"?>'
    '<Response>'
    '<Message>Error</Message>'
    '<MessageCode>0.0</MessageCode>'
    '<Errors>'
    '<Error>'
    '<ErrorCode>0.0</ErrorCode>'
    '<ErrorName>Error message</ErrorName>'
    '<Description>bla bla</Description>'
    '<Suggestion>ble ble</Suggestion>'
    '</Error>'
    '</Errors>'
    '</Response>'
)

_SAMPLE_DELETE_MEDIA_XML = (
    '<?xml version="1.0"?>'
    '<Response>'
    '<Message>Success</Message>'
    '<MessageCode>0.0</MessageCode>'
    '<Success>'
    '<MediaShortLink>%(shortcode)s</MediaShortLink>'
    '</Success>'
    '<Errors>'
    '<Error>'
    '<SourceFile>http://www.com</SourceFile>'
    '<ErrorCode>1</ErrorCode>'
    '<Description>ErrorDescriptionK</Description>'
    '<Suggestion>ErrorSuggestionK</Suggestion>'
    '</Error>'
    '</Errors>'
    '</Response>'
)

MEDIA_SHORT_LINK_REGEX = re.compile('<MediaShortLink>(\w+)</MediaShortLink>')
STATUS_REGEX = re.compile('<Status>(\w+)</Status>')
SOURCE_FILE_REGEX = re.compile('<SourceFile>(.*?)</SourceFile>')


def random_shortcode():
    return '000' + str(uuid.uuid4())[:6]


class Database(object):

    def __init__(self, filename):
        #print "** LOADING **"
        #print open(filename).read()
        self.filename = filename
        self.data = json.load(open(filename))

    def __setitem__(self, key, value):
        self.data[key] = value
        self._save()

    def __delitem__(self, key):
        del self.data[key]
        self._save()

    def items(self):
        return self.data.items()

    def get(self, key, default=None):
        return self.data.get(key, default)

    def __iter__(self):
        return iter(self.data)

    def __getitem__(self, key):
        return self.data[key]

    def _save(self):
        #print "** SAVING **"
        #print self.data
        #print
        json.dump(self.data, open(self.filename, 'w'), indent=2)


"""
db = Database('foo.json')
db['second'] = 'third'
assert db['second'] == 'third'
db = Database('foo.json')
del db['second']
db = Database('foo.json')
db['third'] = 'Stuck'
print '-'*80
print open('foo.json').read()
print
"""


class MainHandler(web.RequestHandler):
    def get(self):
        self.write("hi!")

    @property
    def DATABASE(self):
        try:
            #return Database(json.load(open('local_database.json')))
            return Database('local_database.json')
        except IOError:
            print "No local_database.json file :("
            return Database()

    def post(self):
        from time import sleep
        sleep(1)# hack to slow things down
        xml_incoming = self.get_argument('xml')
        print "INCOMING ".ljust(79, '=')
        print xml_incoming

        if '<Action>GetStatus</Action>' in xml_incoming:
            tag = MEDIA_SHORT_LINK_REGEX.findall(xml_incoming)[0]
            xml_outgoing = self._get_status(tag)
        elif '<Action>GetMediaList</Action>' in xml_incoming:
            status = STATUS_REGEX.findall(xml_incoming)[0]
            xml_outgoing = self._get_medialist(status)
        elif '<Action>AddMediaLite</Action>' in xml_incoming:
            source_file = SOURCE_FILE_REGEX.findall(xml_incoming)[0]
            xml_outgoing = self._add_media(source_file)
        elif '<Action>DeleteMedia</Action>' in xml_incoming:
            tag = MEDIA_SHORT_LINK_REGEX.findall(xml_incoming)[0]
            xml_outgoing = self._delete_media(tag)
        else:
            raise NotImplementedError(xml_incoming)

        print "OUTGOING ".ljust(79, '=')
        print xml_outgoing
        self.write(xml_outgoing)

    def _get_status(self, tag):
        status = self.DATABASE.get(tag, {'status': 'Finished'})['status']

        xml_outgoing = (
            GET_STATUS_XML
            % {'tag': tag,
               'status': status,
               }
        )
        return xml_outgoing

    def _get_medialist(self, status):
        tags = []
        for tag, stuff in self.DATABASE.items():
            if isinstance(stuff, dict) and stuff.get('status') == status:
                tags.append(tag)

        media_blocks = [
            _SAMPLE_MEDIALIST_MEDIA_XML
            % {'tag': tag, 'status': status}
            for tag in tags
        ]
        xml_outgoing = (
            SAMPLE_MEDIALIST_XML % {'media': ''.join(media_blocks)}
        )
        return xml_outgoing

    def _add_media(self, source_file):
        shortcode = None
        result = None

        if source_file not in self.DATABASE:
            for key in self.DATABASE:
                if source_file.startswith(key):
                    result = self.DATABASE[key]
                    break

        if source_file in self.DATABASE:
            result = self.DATABASE[source_file]

        if result:
            if result.get('shortcode'):
                if result.get('shortcode') == '*random_shortcode*':
                    shortcode = random_shortcode()
                    print "Generating new shortcode", shortcode
                    self.DATABASE[shortcode] = {'status': 'Processing'}

        if shortcode:
            return _SAMPLE_ADD_MEDIA_XML % {'shortcode': shortcode}
        else:
            return _SAMPLE_ADD_MEDIA_ERROR_XML

    def _delete_media(self, tag):
        del self.DATABASE[tag]
        return _SAMPLE_DELETE_MEDIA_XML % {'shortcode': tag}


routes = [
    (r"/", MainHandler),
    #(r"/benchmark", BenchmarkHandler),
]

if __name__ == "__main__":
    options.parse_command_line()
    application = web.Application(
        routes,
        debug=options.debug,
    )

    print "Starting tornado on port", options.port
    application.listen(options.port)
    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        pass
