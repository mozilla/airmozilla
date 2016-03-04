from django_jinja import library


@library.global_function
def max_(*args):
    return max(*args)
