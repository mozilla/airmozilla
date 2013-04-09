from optparse import make_option
from django.core.management.base import NoArgsCommand
from airmozilla.manage.pestering import pester


class Command(NoArgsCommand):  # pragma: no cover

    option_list = NoArgsCommand.option_list + (
        make_option('-n', '--dry-run', action='store_true', dest='dry_run',
                    default=False,
                    help="Do everything except actually sending."),
        make_option('-f', '--force', action='store_true', dest='force_run',
                    default=False, help="Ignore any cache locks."),
    )

    def handle(self, *args, **options):
        emails_sent = pester(
            dry_run=options['dry_run'],
            force_run=options['force_run'],
        )
        if options['dry_run'] or int(options['verbosity']) > 1:
            for email, subject, message in emails_sent:
                print 'TO:', email
                print 'SUBJECT:', subject
                print
                print message
                print '\n'
                print '-' * 60
                print '\n'
