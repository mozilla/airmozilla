#
# {{ header }}
#

MAILTO=peterbe@mozilla.com

HOME=/tmp

# Every 1 hour
0 */1 * * * {{ cron }} send_unsent_tweets 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|simplejson|from pkg_resources)'

# Every 10 minutes
*/10 * * * * {{ cron }} auto_archive 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|simplejson|from pkg_resources)'

# Daily
7 0 * * * {{ cron }} pester_approvals 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|simplejson|from pkg_resources)'

# Every 2 hours (10 minutes past)
10 */2 * * * {{ cron }} synchronize_vidly_submissions 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|simplejson|from pkg_resources)'

# Every hour
0 */1 * * * {{ cron }} cron_ping 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|simplejson|from pkg_resources)'

# Every 30 minutes
*/30 * * * * {{ cron }} update_event_hit_stats 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|simplejson|from pkg_resources)'

# Every 15 minutes
*/15 * * * * {{ cron }} fetch_durations 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|simplejson|from pkg_resources)'

# Every 12 minutes
*/12 * * * * {{ cron }} fetch_screencaptures 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|simplejson|from pkg_resources)'

# Every 12 minutes
*/12 * * * * {{ cron }} import_screencaptures 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|simplejson|from pkg_resources)'

# Every 10 minutes
*/10 * * * * {{ cron }} autocompeter_update 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|simplejson|from pkg_resources)'

# Every day at 8AM
8 0 * * * * {{ cron }} autocompeter_reset 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|simplejson|from pkg_resources)'

# Every 10 minutes
*/10 * * * * {{ cron }} send_new_event_emails 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|simplejson|from pkg_resources)'



# Every 15 minutes
*/15 * * * * {{ cron }} tweet_new_published_events 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|simplejson|from pkg_resources)'

# Every 5 minutes
*/5 * * * * {{ cron }} render_popcorn 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|simplejson|from pkg_resources)'

# Every Sunday at 8AM
0 8 * * 0 {{ cron }} related_content_reindex 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|simplejson|from pkg_resources)'


# Every 10 minutes
*/10 * * * * {{ cron }} related_content_index 2>&1 | grep -Ev '(DeprecationWarning|UserWarning|simplejson|from pkg_resources)'


MAILTO=root
