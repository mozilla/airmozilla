import sys
import functools
import contextlib
import traceback
from StringIO import StringIO

from .models import CronLog


@contextlib.contextmanager
def redirect_streams(stdout, stderr):
    sys.stdout = stdout
    sys.stderr = stderr
    yield
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__


def capture(f):

    @functools.wraps(f)
    def inner(*args, **kwargs):
        stdout = StringIO()
        stderr = StringIO()
        # L = open('/tmp/log.log', 'a')
        with redirect_streams(stdout, stderr):
            try:
                result = f(*args, **kwargs)
                CronLog.objects.create(
                    job=f.func_name,
                    stdout=stdout.getvalue(),
                    stderr=stderr.getvalue()
                )
                # L.write('RESULT:%r\n'% result)
                return result
            except Exception:
                exc_type, exc_value, exc_tb = sys.exc_info()
                CronLog.objects.create(
                    job=f.func_name,
                    stdout=stdout.getvalue(),
                    stderr=stderr.getvalue(),
                    exc_type=str(exc_type),
                    exc_value=str(exc_value),
                    exc_traceback=''.join(traceback.format_tb(exc_tb))
                )
                raise

    return inner
