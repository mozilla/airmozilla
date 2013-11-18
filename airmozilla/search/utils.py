STOPWORDS = (
    "a able about across after all almost also am among an and "
    "any are as at be because been but by can cannot could dear "
    "did do does either else ever every for from get got had has "
    "have he her hers him his how however i if in into is it its "
    "just least let like likely may me might most must my "
    "neither no nor not of off often on only or other our own "
    "rather said say says she should since so some than that the "
    "their them then there these they this tis to too twas us "
    "wants was we were what when where which while who whom why "
    "will with would yet you your".split()
)


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
