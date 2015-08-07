from django.db.utils import ProgrammingError
from django.core.management.base import BaseCommand


class Command(BaseCommand):  # pragma: no cover
    """We USED to have djcelery installed but it was an ancient version.
    And we never used it. Because those tables lingering, we can't execute
    `./manage.py syncdb` and `./manage.py migrate`

    There's no harm in deleting these tables because the worst thing
    that can happen is that we lose some pending jobs.
    However, at the time of writing we don't have a message queue working.
    """
    def handle(self, *args, **options):
        from django.db import connection
        cursor = connection.cursor()
        try:
            cursor.execute("""
            DROP TABLE  celery_taskmeta;
            DROP TABLE  celery_tasksetmeta;
            DROP TABLE  djcelery_taskstate;
            DROP TABLE  djcelery_workerstate;
            DROP TABLE  djcelery_periodictasks;
            DROP TABLE  djcelery_periodictask;
            DROP TABLE  djcelery_intervalschedule;
            DROP TABLE  djcelery_crontabschedule;

            DELETE FROM south_migrationhistory WHERE app_name = 'djcelery';
            """)
            connection.commit()
        except ProgrammingError as exception:
            print "Unable delete old celery tabes"
            print exception

        cursor = connection.cursor()
        try:
            cursor.execute("""
            DROP TABLE  djkombu_message;
            DROP TABLE  djkombu_queue;

            DELETE FROM south_migrationhistory WHERE app_name = 'django';
            """)
            connection.commit()
        except ProgrammingError as exception:
            print "Unable delete old djkombu tabes"
            print exception
