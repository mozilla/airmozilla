#
# {{ header }}
#

MAILTO=peterbe@mozilla.com

HOME=/tmp

# Every 5 minutes
*/5 * * * * {{ cron }} send_unsent_tweets 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|from pkg_resources)'

# Every 5 minutes
*/5 * * * * {{ cron }} auto_archive 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|from pkg_resources)'

# Daily
7 0 * * * {{ cron }} pester_approvals 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|from pkg_resources)'

# Every minute
*/1 * * * * {{ cron }} cron_ping 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|from pkg_resources)'

MAILTO=root
