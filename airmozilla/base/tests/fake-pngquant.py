#!/usr/bin/env python

import sys
import base64

"""
This is a very crude a dumb script that act as a fake pngquant executable.
You have to use the `-o destination.png` flags. E.g.

    fake-pngquant.py -o /dest/ination.png -- /sour/ce.png

It will always produce the same image.
"""


PNG = (
    'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAABGdBTUEAALGPC/xhBQAAACBjS'
    'FJNAAB6JgAAgIQAAPoAAACA6AAAdTAAAOpgAAA6mAAAF3CculE8AAAACXBIWXMAAAsTAAALEw'
    'EAmpwYAAABWWlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPHg6eG1wbWV0YSB4bWxuczp4PSJ'
    'hZG9iZTpuczptZXRhLyIgeDp4bXB0az0iWE1QIENvcmUgNS40LjAiPgogICA8cmRmOlJERiB4'
    'bWxuczpyZGY9Imh0dHA6Ly93d3cudzMub3JnLzE5OTkvMDIvMjItcmRmLXN5bnRheC1ucyMiP'
    'gogICAgICA8cmRmOkRlc2NyaXB0aW9uIHJkZjphYm91dD0iIgogICAgICAgICAgICB4bWxucz'
    'p0aWZmPSJodHRwOi8vbnMuYWRvYmUuY29tL3RpZmYvMS4wLyI+CiAgICAgICAgIDx0aWZmOk9'
    'yaWVudGF0aW9uPjE8L3RpZmY6T3JpZW50YXRpb24+CiAgICAgIDwvcmRmOkRlc2NyaXB0aW9u'
    'PgogICA8L3JkZjpSREY+CjwveDp4bXBtZXRhPgpMwidZAAABPUlEQVQYGWNggIL/DQ1MMDaM/'
    'r8qlBnGZgQx/v//zwgE/xkm/ecrVb5pxfn22f+mOKdjQKnPDP8ZGIHwP9gUkKL9hYERE37NPy'
    'jEybKdQVJux9YFOfv+H2WwBClqaGBgYgGZeDGQQYyD5X638b9ZMptuMP7rYTZkFGJyNLn/8fH'
    'c/x832jDyM7wDm/hHWluH9ecFybt3Tvx7+PDjvwt7zvzZtvUEAys7hyrDbQYtkGFghY8efPzy'
    '7RfXP1YGbSbVb9f/BL449DdG9xCDiPDnr9c/B34AKYSDvSGiaz+Wcf+/mMHwf0eQ6v/f23T/v'
    '7hgvxKmgHlVKAPz6msM/z9e+3ac6Q23HNMnfnExia9fXrM+2Lru7MOq3YcY3v//D7EZ6C0oA6'
    'hdj4FBHUipwkz6/x8tfFcxMMADF6EIYQAAENp/dn0/huoAAAAASUVORK5CYII='
)


if __name__ == '__main__':
    args = sys.argv[1:]
    destination = args[args.index('-o') + 1]
    with open(destination, 'wb') as f:
        f.write(base64.b64decode(PNG))
