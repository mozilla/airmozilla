#
# {{ header }}
#

# MAILTO=peterbe@mozilla.com

HOME=/tmp

# Every 5 minutes
*/5 * * * * {{ cron }} send_unsent_tweets

# Every 5 minutes
*/5 * * * * {{ cron }} auto_archive

# Daily
7 0 * * * {{ cron }} pester_approvals

# Every minute
*/1 * * * * {{ cron }} cron_ping

MAILTO=root
