#
# {{ header }}
#

MAILTO=peterbe@mozilla.com

HOME=/tmp

# Every 5 minutes
*/5 * * * * {{ cron }} send_unsent_tweets 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|from pkg_resources)'

# Every 2 minutes
*/2 * * * * {{ cron }} auto_archive 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|from pkg_resources)'

# Daily
7 0 * * * {{ cron }} pester_approvals 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|from pkg_resources)'

# Every hour
0 */1 * * * {{ cron }} cron_ping 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|from pkg_resources)'

# Every 10 minutes
*/10 * * * * {{ cron }} update_event_hit_stats 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|from pkg_resources)'

# Every 15 minutes
*/15 * * * * {{ cron }} fetch_durations 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|from pkg_resources)'


MAILTO=root
