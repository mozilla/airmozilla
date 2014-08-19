def get_url_prefix(filename):
    with open(filename) as f:
        content = f.read()
        lines = [x for x in content.splitlines() if x.count('UrlPrefix')]
        active_line = [x for x in lines if not x.strip().startswith("'")][0]
        return active_line.split('"')[1]


def check(filename):
    line = get_url_prefix(filename)
    print repr(line)
    if 'allizom.org' in line:
        print "*" * 80
        print "WARNING"
        print
        print "You're using UrlPrefix", line
        print
        print "*" * 80
    elif 'air.mozilla.org' not in line:
        print "*" * 80
        print "ERROR"
        print
        print "You're using UrlPrefix", line
        print
        print "Refusing to build the zip."
        print "This tool is for making a productionish zip file."
        print "For local development, use `make install` instead."
        print "*" * 80
        return 1

    return 0


if __name__ == '__main__':
    import sys
    if not sys.argv[1:]:
        print "USAGE %s some/file.brs" % __file__
        sys.exit(10)

    sys.exit(check(sys.argv[1]))
