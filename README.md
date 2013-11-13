Air Mozilla
===========

Air Mozilla is the Internet multimedia presence of Mozilla, with live and
pre-recorded shows, interviews, news snippets, tutorial videos, and
features about the Mozilla community.

We are rebuilding Air Mozilla to use [Mozilla's Playdoh][gh-playdoh],
a web application template based on [Django][django],
and adding some neat features along the way.

Tracking bug: https://bugzilla.mozilla.org/show_bug.cgi?id=712717

Wiki page: https://wiki.mozilla.org/Air_Mozilla


Tests and test coverage
-----------------------
Included is a set of comprehensive tests, which you can run by:
``./manage.py test``

To see the tests' code coverage, use:
``./manage.py test --with-coverage --cover-erase --cover-html --cover-package=airmozilla``


Migrations
----------
We're using [South][south] to handle database migrations.
To generate a schema migration, make changes to models.py, then run:

``./manage.py schemamigration airmozilla.main --auto``

or

``./manage.py schemamigration airmozilla.comments --auto``

To generate a blank data migration, use:

``./manage.py datamigration airmozilla.main data_migration_name``

Then fill in the generated file with logic, fixtures, etc.

To apply migrations:

``./manage.py migrate airmozilla.main airmozilla.comments``

In each command, replace airmozilla.main with the appropriate app.


Requirements
------------
See the ``requirements/`` directory for installation dependencies.
This app requires a working install of PIL with libjpeg and libpng.


First run
-----------------------
```
./manage.py syncdb
./manage.py migrate
```

If you'd like to create a default set of example groups with useful permissions
(Event Organizers, Experienced Event Organizers, PR, Producer):

``./manage.py create_mozilla_groups``

Since we're using BrowserID for log-in, you'll need to manually set up your
account as a superuser.  Log in to the site, then run the shell command:
```
./manage.py shell
>>> from django.contrib.auth.models import User
>>> my_user = User.objects.get(email='my@email.com')
>>> my_user.is_superuser = True
>>> my_user.is_staff = True
>>> my_user.save()
```

IRC
---
irc://irc.mozilla.org/airmozilla-dev

[django]: http://www.djangoproject.com/
[gh-playdoh]: https://github.com/mozilla/playdoh
[south]: http://south.aeracode.org/


Cron jobs
---------

All cron jobs are managed by two files: First
``airmozilla/manage/crons.py`` where you kick things off. Then, later
the crontab file is compiled and installed by
``bin/crontab/crontab.tpl``. These are the two files you need to edit
to change, add or remove a cron execution.


Twitter
-------

To test tweeting locally, what you need to do is set up some fake
authentication credentials and lastly enable a debugging backend. So,
add this to your settings/local.py:

    TWITTER_USERNAME = 'airmozilla_dev'
    TWITTER_CONSUMER_KEY = 'something'
    TWITTER_CONSUMER_SECRET = 'something'
    TWITTER_ACCESS_TOKEN = 'something'
    TWITTER_ACCESS_TOKEN_SECRET = 'something'

Now, to avoid actually using HTTP to post this message to
api.twitter.com instead add this to your settings/local.py:

    TWEETER_BACKEND = 'airmozilla.manage.tweeter.ConsoleTweeter'

That means that all tweets will be sent to stdout instead of actually
being attempted.

To send unsent tweets, you need to call:

    ./manage.py cron send_unsent_tweets

This can be called again and again and internally it will take care of
not sending the same tweet twice.

If errors occur when trying to send, the tweet will be re-attempted
till the error finally goes away.


Deployment
----------

Deployment of dev, stage and prod is all done using Chief. More will
be written about it soon.


Bit.ly URL Shortener
--------------------

To generate a Bit.ly access token you need the right email address and
password. If you have access you can go to
https://bugzilla.mozilla.org/show_bug.cgi?id=870385#c2

To generate it use this command:

    curl -u "EMAIL:PASSWORD" -X POST "https://api-ssl.bitly.com/oauth/access_token"

That will spit out a 40 character code which you set in
settings/local.py for the ``BITLY_ACCESS_TOKEN`` setting.


About the database
------------------

Even though we use the Django ORM which is database engine agnostic,
we have to have PostgreSQL because we rely on its ability to do full
text index searches.
