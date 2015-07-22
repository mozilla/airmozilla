#!/usr/bin/env python

# Copyright (c) 2012, Akamai Technologies, Inc.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of Akamai Technologies nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL AKAMAI TECHNOLOGIES BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

APP_VERSION = '2.0.6'

import binascii
import hashlib
import hmac
import optparse
import os
import re
import sys
import time
import urllib

# Force the local timezone to be GMT.
os.environ['TZ'] = 'GMT'
time.tzset()

class AkamaiTokenError(Exception):
    def __init__(self, text):
        self._text = text

    def __str__(self):
        return 'AkamaiTokenError:%s' % self._text

    def _getText(self):
        return str(self)
    text = property(_getText, None, None,
        'Formatted error text.')


class AkamaiTokenConfig:
    def __init__(self):
        self.ip = ''
        self.start_time = None
        self.window = 300
        self.acl = ''
        self.session_id = ''
        self.data = ''
        self.url = ''
        self.salt = ''
        self.field_delimiter = '~'
        self.algo = 'sha256'
        self.param = None
        self.key = 'aabbccddeeff00112233445566778899'
        self.early_url_encoding = False


class AkamaiToken:
    def __init__(self, token_type=None, token_name='hdnts', ip=None,
                 start_time=None, end_time=None, window_seconds=None, url=None,
                 acl=None, key=None, payload=None, algorithm='sha256',
                 salt=None, session_id=None, field_delimiter=None,
                 acl_delimiter=None, escape_early=False,
                 escape_early_upper=False, verbose=False):
        self._token_type = token_type
        self._token_name = token_name
        self._ip = ip
        self._start_time = start_time
        self._end_time = end_time
        self._window_seconds = window_seconds
        self._url = url
        self._acl = acl
        self._key = key
        self._payload = payload
        self._algorithm = algorithm
        if not self._algorithm:
            self._algorithm = 'sha256'
        self._salt = salt
        self._session_id = session_id
        self._field_delimiter = field_delimiter
        if not self._field_delimiter:
            self._field_delimiter = '~'
        self._acl_delimiter = acl_delimiter
        if not self._acl_delimiter:
            self._acl_delimiter = '!'
        self._escape_early = escape_early
        self._escape_early_upper = escape_early_upper
        self._verbose = verbose
        self._warnings = []

    def _getWarnings(self):
        return self._warnings

    warnings = property(_getWarnings, None, None,
        'List of warnings from the last generate request')

    def escapeEarly(self, text):
        if self._escape_early or self._escape_early_upper:
            # Only escape the text if we are configured for escape early.
            new_text = urllib.quote_plus(text)
            if self._escape_early_upper:
                def toUpper(match):
                    return match.group(1).upper()
                return re.sub(r'(%..)', toUpper, new_text)
            else:
                def toLower(match):
                    return match.group(1).lower()
                return re.sub(r'(%..)', toLower, new_text)

        # Return the original, unmodified text.
        return text

    def generate_token(self, token_config):
        """
        Backwards compatible interface.

        """
        # Copy the config parameters where they need to be.
        self._token_name = token_config.param
        self._ip = token_config.ip
        self._start_time = token_config.start_time
        self._end_time = 0
        self._window_seconds = token_config.window
        self._url = token_config.url
        self._acl = token_config.acl
        self._key = token_config.key
        self._payload = token_config.data
        self._algorithm = token_config.algo
        if not self._algorithm:
            self._algorithm = 'sha256'
        self._salt = token_config.salt
        self._session_id = token_config.session_id
        self._field_delimiter = token_config.field_delimiter
        if not self._field_delimiter:
            self._field_delimiter = '~'
        self._acl_delimiter = '!'
        self._escape_early = bool(str(token_config.early_url_encoding).lower()
            in ('yes', 'true'))
        return self.generateToken()

    def generateToken(self):
        if not self._token_name:
            self._token_name = 'hdnts'

        if not self._algorithm:
            self._algorithm = 'sha256'

        if str(self._start_time).lower() == 'now':
            # Initialize the start time if we are asked for a starting time of
            # now.
            self._start_time = int(time.mktime(time.gmtime()))
        elif self._start_time is not None:
            try:
                self._start_time = int(self._start_time)
            except:
                raise AkamaiTokenError('start_time must be numeric or now')

        if self._end_time is not None:
            try:
                self._end_time = int(self._end_time)
            except:
                raise AkamaiTokenError('end_time must be numeric.')

        if self._window_seconds is not None:
            try:
                self._window_seconds = int(self._window_seconds)
            except:
                raise AkamaiTokenError('window_seconds must be numeric.')

        if self._end_time <= 0:
            if self._window_seconds > 0:
                if self._start_time is None:
                    # If we have a duration window without a start time,
                    # calculate the end time starting from the current time.
                    self._end_time = int(time.mktime(time.gmtime())) + \
                        self._window_seconds
                else:
                    self._end_time = self._start_time + self._window_seconds
            else:
                raise AkamaiTokenError('You must provide an expiration time or '
                    'a duration window.')

        if self._end_time < self._start_time:
            self._warnings.append(
                'WARNING:Token will have already expired.')

        if self._key is None or len(self._key) <= 0:
            raise AkamaiTokenError('You must provide a secret in order to '
                'generate a new token.')

        if ((self._acl is None and self._url is None) or
            self._acl is not None and self._url is not None and
            (len(self._acl) <= 0) and (len(self._url) <= 0)):
            raise AkamaiTokenError('You must provide a URL or an ACL.')

        if (self._acl is not None and self._url is not None and
            (len(self._acl) > 0) and (len(self._url) > 0)):
            raise AkamaiTokenError('You must provide a URL OR an ACL, '
                'not both.')

        if self._verbose:
            print('''
Akamai Token Generation Parameters
Token Type      : %s
Token Name      : %s
Start Time      : %s
Window(seconds) : %s
End Time        : %s
IP              : %s
URL             : %s
ACL             : %s
Key/Secret      : %s
Payload         : %s
Algo            : %s
Salt            : %s
Session ID      : %s
Field Delimiter : %s
ACL Delimiter   : %s
Escape Early    : %s
Generating token...''' % (
    ''.join([str(x) for x in [self._token_type] if x is not None]),
    ''.join([str(x) for x in [self._token_name] if x is not None]),
    ''.join([str(x) for x in [self._start_time] if x is not None]),
    ''.join([str(x) for x in [self._window_seconds] if x is not None]),
    ''.join([str(x) for x in [self._end_time] if x is not None]),
    ''.join([str(x) for x in [self._ip] if x is not None]),
    ''.join([str(x) for x in [self._url] if x is not None]),
    ''.join([str(x) for x in [self._acl] if x is not None]),
    ''.join([str(x) for x in [self._key] if x is not None]),
    ''.join([str(x) for x in [self._payload] if x is not None]),
    ''.join([str(x) for x in [self._algorithm] if x is not None]),
    ''.join([str(x) for x in [self._salt] if x is not None]),
    ''.join([str(x) for x in [self._session_id] if x is not None]),
    ''.join([str(x) for x in [self._field_delimiter] if x is not None]),
    ''.join([str(x) for x in [self._acl_delimiter] if x is not None]),
    ''.join([str(x) for x in [self._escape_early] if x is not None])))

        hash_source = ''
        new_token = ''

        if self._ip:
            new_token += 'ip=%s%c' % (self.escapeEarly(self._ip),
                self._field_delimiter)

        if self._start_time is not None:
            new_token += 'st=%d%c' % (self._start_time, self._field_delimiter)

        new_token += 'exp=%d%c' % (self._end_time, self._field_delimiter)

        if self._acl:
            new_token += 'acl=%s%c' % (self.escapeEarly(self._acl),
                self._field_delimiter)

        if self._session_id:
            new_token += 'id=%s%c' % (self.escapeEarly(self._session_id),
                self._field_delimiter)

        if self._payload:
            new_token += 'data=%s%c' % (self.escapeEarly(self._payload),
                self._field_delimiter)

        hash_source += new_token
        if self._url and not self._acl:
            hash_source += 'url=%s%c' % (self.escapeEarly(self._url),
                self._field_delimiter)

        if self._salt:
            hash_source += 'salt=%s%c' % (self._salt, self._field_delimiter)

        if self._algorithm.lower() not in ('sha256', 'sha1', 'md5'):
            raise AkamaiTokenError('Unknown algorithm')
        token_hmac = hmac.new(
            binascii.a2b_hex(self._key),
            hash_source.rstrip(self._field_delimiter),
            getattr(hashlib, self._algorithm.lower())).hexdigest()
        new_token += 'hmac=%s' % token_hmac

        return '%s=%s' % (self._token_name, new_token)

if __name__ == '__main__':
    usage = 'python akamai_token_v2.py [options]\n'\
            'ie.\n' \
            'python akamai_token_v2.py'
    parser = optparse.OptionParser(usage=usage, version=APP_VERSION)
    parser.add_option(
        '-t', '--token_type',
        action='store', type='string', dest='token_type',
        help='Select a preset: (Not Supported Yet) [2.0, 2.0.2 ,PV, Debug]')
    parser.add_option(
        '-n', '--token_name',
        action='store', type='string', dest='token_name',
        help='Parameter name for the new token. [Default:hdnts]')
    parser.add_option(
        '-i', '--ip',
        action='store', type='string', dest='ip_address',
        help='IP Address to restrict this token to.')
    parser.add_option(
        '-s', '--start_time',
        action='store', type='string', dest='start_time',
        help='What is the start time. (Use now for the current time)')
    parser.add_option(
        '-e', '--end_time',
        action='store', type='string', dest='end_time',
        help='When does this token expire? --end_time overrides --window [Used for:URL or COOKIE]')
    parser.add_option(
        '-w', '--window',
        action='store', type='string', dest='window_seconds',
        help='How long is this token valid for?')
    parser.add_option(
        '-u', '--url',
        action='store', type='string', dest='url',
        help='URL path. [Used for:URL]')
    parser.add_option(
        '-a', '--acl',
        action='store', type='string', dest='access_list',
        help='Access control list delimited by ! [ie. /*]')
    parser.add_option(
        '-k', '--key',
        action='store', type='string', dest='key',
        help='Secret required to generate the token.')
    parser.add_option(
        '-p', '--payload',
        action='store', type='string', dest='payload',
        help='Additional text added to the calculated digest.')
    parser.add_option(
        '-A', '--algo',
        action='store', type='string', dest='algorithm',
        help='Algorithm to use to generate the token. (sha1, sha256, or md5) [Default:sha256]')
    parser.add_option(
        '-S', '--salt',
        action='store', type='string', dest='salt',
        help='Additional data validated by the token but NOT included in the token body.')
    parser.add_option(
        '-I', '--session_id',
        action='store', type='string', dest='session_id',
        help='The session identifier for single use tokens or other advanced cases.')
    parser.add_option(
        '-d', '--field_delimiter',
        action='store', type='string', dest='field_delimiter',
        help='Character used to delimit token body fields. [Default:~]')
    parser.add_option(
        '-D', '--acl_delimiter',
        action='store', type='string', dest='acl_delimiter',
        help='Character used to delimit acl fields. [Default:!]')
    parser.add_option(
        '-x', '--escape_early',
        action='store_true', default=False, dest='escape_early',
        help='Causes strings to be url encoded before being used. (legacy 2.0 behavior)')
    parser.add_option(
        '-X', '--escape_early_upper',
        action='store_true', default=False, dest='escape_early_upper',
        help='Causes strings to be url encoded before being used. (legacy 2.0 behavior)')
    parser.add_option(
        '-v', '--verbose',
        action='store_true', default=False, dest='verbose',
        help='')
    (options, args) = parser.parse_args()
    try:
        generator = AkamaiToken(
            options.token_type,
            options.token_name,
            options.ip_address,
            options.start_time,
            options.end_time,
            options.window_seconds,
            options.url,
            options.access_list,
            options.key,
            options.payload,
            options.algorithm,
            options.salt,
            options.session_id,
            options.field_delimiter,
            options.acl_delimiter,
            options.escape_early,
            options.escape_early_upper,
            options.verbose)
        new_token = generator.generateToken()
        if generator.warnings:
            print('\n'.join(generator.warnings))
        print('%s' % new_token)
    except AkamaiTokenError, ex:
        print('%s\n' % ex)
        sys.exit(1)
    except Exception, ex:
        print(str(ex))
        sys.exit(1)

