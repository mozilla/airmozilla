from airmozilla.base.utils import STOPWORDS


def _find_words(q):
    return [w for w in q.split() if len(w) > 1 and w.lower() not in STOPWORDS]


def possible_to_or_query(q):
    """return true if it's possible to turn this query into something with
    | characters in between"""
    # bail if there are some strange characters in there already
    if '&' in q or '|' in q:
        return False
    # Count the number of words that aren't stopwords or simply too short
    words = _find_words(q)
    return len(words) > 1


def make_or_query(q):
    words = _find_words(q)
    return '|'.join(words)
