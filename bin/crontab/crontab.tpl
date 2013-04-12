#
# {{ header }}
#

# MAILTO=peterbe@mozilla.com

HOME=/tmp

# Every minute!
#* * * * * {{ cron }}

# Every hour.
#42 * * * * {{ django }} cleanup

# Every 5 minutes
*/5 * * * * {{ cron }} send_unsent_tweets

# Daily
7 0 * * * {{ cron }} pester_approvals


# Every 2 hours.
#1 */2 * * * {{ cron }} something

# Etc...

MAILTO=root
