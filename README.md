Air Mozilla
=======

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
``./manage.py test --with-coverage --cover-html --cover-package=airmozilla``


Migrations
----------
We're using [South][south] to handle database migrations.
To generate a schema migration, make changes to models.py, then run:

``./manage.py schemamigration airmozilla.main --auto``

To generate a blank data migration, use:

``./manage.py datamigration airmozilla.main data_migration_name``

Then fill in the generated file with logic, fixtures, etc.

To apply migrations:

``./manage.py migrate airmozilla.main``

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
