from jingo import register


@register.function
def max_(*args):
    return max(*args)
