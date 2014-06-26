# -*- coding: utf-8 -*
#
# Split search string - Useful when building advanced search application
# By: Peter Bengtsson, mail@peterbe.com
# May 2008-2010
# Python
#
# Taken from http://www.peterbe.com/plog/split_search

__version__ = '1.4'

"""

  split_search(searchstring [str or unicode],
               keywords [list or tuple])

  Splits the search string into a free text part and a dictionary of keyword
  pairs. For example, if you search for 'Something from: Peter to: Lukasz'
  this function will return
  'Something', {'from':'Peter', 'to':'Lukasz'}

  It works equally well with unicode strings.

  Any keywords in the search string that isn't recognized is considered text.

"""

import re


def split_search(q, keywords):
    params = {}
    s = []
    if re.findall('[^\w]', ''.join(keywords)):
        raise ValueError("keywords can not contain non \w characters")

    regex = re.compile(r'\b(%s):' % '|'.join(keywords), re.I)
    bits = regex.split(q)
    if len(bits) == 1:
        # there was no keyword at all
        return q, {}

    skip_next = False
    for i, bit in enumerate(bits):
        if skip_next:
            skip_next = False
        else:
            if bit.lower() in keywords:
                params[bit.lower()] = bits[i + 1].strip()
                skip_next = True
            elif bit.strip():
                s.append(bit.strip())

    return ' '.join(s), params
