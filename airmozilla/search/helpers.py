from jingo import register


@register.filter
def highlight(text, q):
    #print (text, q)
    return text
