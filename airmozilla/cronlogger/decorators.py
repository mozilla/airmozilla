import time
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
        with redirect_streams(stdout, stderr):
            try:
                t0 = time.time()
                result = f(*args, **kwargs)
                t1 = time.time()
                CronLog.objects.create(
                    job=f.func_name,
                    stdout=stdout.getvalue(),
                    stderr=stderr.getvalue(),
                    duration='%.3f' % (t1 - t0),
                )
                return result
            except Exception:
                t1 = time.time()
                exc_type, exc_value, exc_tb = sys.exc_info()
                CronLog.objects.create(
                    job=f.func_name,
                    stdout=stdout.getvalue(),
                    stderr=stderr.getvalue(),
                    exc_type=str(exc_type),
                    exc_value=str(exc_value),
                    exc_traceback=''.join(traceback.format_tb(exc_tb)),
                    duration='%.3f' % (t1 - t0),
                )
                raise

    return inner
