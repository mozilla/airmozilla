from jingo import register


@register.function
def star_tag(id, extra_classes=None):
    extra_classes = extra_classes or []
    if isinstance(extra_classes, basestring):
        extra_classes = [extra_classes]
    extra_classes.insert(0, 'star')
    return '<a class="{0}" data-id="{1}" data-star-on="Remove star" data-star-off="Save as a starred event"></a>'.format(
        ' '.join(extra_classes),
        id
    )
