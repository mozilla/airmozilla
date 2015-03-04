Air Mozilla
===========

[![Build Status](https://travis-ci.org/mozilla/airmozilla.svg?branch=master)](https://travis-ci.org/mozilla/airmozilla)
[![Coverage Status](https://coveralls.io/repos/mozilla/airmozilla/badge.png?branch=master)](https://coveralls.io/r/mozilla/airmozilla?branch=master)


Live: [https://air.mozilla.org](https://air.mozilla.org)
Stage: [https://air.allizom.org](https://air.allizom.org)
Dev: [https://air-dev.allizom.org](https://air-dev.allizom.org)

Air Mozilla is the Internet multimedia presence of Mozilla, with live and
pre-recorded shows, interviews, news snippets, tutorial videos, and
features about the Mozilla community.

Wiki page: https://wiki.mozilla.org/Air_Mozilla

Most of this information is also available on

[https://air.mozilla.org/contribute.json](https://air.mozilla.org/contribute.json)


How to get it running locally from scratch
------------------------------------------

### First of all...

All of these manual steps can be done with one optimistic script. All you
need is to have Python (2.6 or 2.7) installed.

[Download this file](https://raw.githubusercontent.com/mozilla/airmozilla/master/devup.py)
and manually run:

    python devup.py

It will ask you a series of questions and how and where you want it installed.

### Doing it the manual way...

This section assumes you know about and are using a
[virtualenv](http://www.virtualenv.org/).
If you're not familiar with `virtualenv`, that's fine. You can use your "system python"
but a virtualenv is advantageous because you get a self-contained python system
that doesn't affect and isn't affected by any other python projects on your
computer.

Also, these instructions are **geared towards developers** working on the code.
Not system people deploying the code for production.

**Step 1 - The stuff you need**

You're going to need Git, Python 2.6 or Python 2.7, a PostgreSQL database
(partially works with MySQL and SQLite too) and the necessary python dev
libraries so you can install binary python packages. On a mac, that means you
need to install XCode and on Linux you'll need to install `python-dev`.

[This article on pyladies.com](http://www.pyladies.com/blog/Get-Your-Mac-Ready-for-Python-Programming/)
has a lot of useful information.

Once you have a virtualenv you want to use, you need to install all the
dependencies. You do this with:

    pip install -r requirements.txt
    pip install -r dev-requirements.txt

The second file is necessary so you can

**Step 2 - Get the code**

Note: We're assuming you have already activated a `virtualenv` which will
have its own `pip`.

Note 2: Windows users, before you start cloning you need to make sure you're not going to
use the git protocol to clone any submodule, otherwise you will get ``fatal: read error: Invalid argument``
errors.

```
git config --global url."https://".insteadOf git://
```

```
git clone https://github.com/mozilla/airmozilla.git
cd airmozilla
pip install -r requirements.txt
```

**Step 3 - Create a database**

To create a database in PostgreSQL there are different approaches. The simplest
is the `createdb` command. How you handle credentials, roles and permissions is
generally out of scope for this tutorial.

```
createdb -E UTF8 airmozilla
```

You might at that point need to supply a specific username and/or password.
Whichever it is, take a note of it because you'll need it to set up your settings.

**Step 4 - Set up the settings**

The first thing to do is to copy the settings "template".

```
cp airmozilla/settings/local.py-dist airmozilla/settings/local.py
```
Now open that `airmozilla/settings/local.py` in your editor and we'll go
through some essential bits.

```
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'airmozilla',
        'USER': 'username',
        'PASSWORD': 'password',
        'HOST': '',
        'PORT': '',
    },
    # 'slave': {
    #     ...
    # },
}
```
Here, replace `username` and `password` accordingly.
If you want to use MySQL, which should work except the Search, you replace
the `ENGINE` setting with `django.db.backends.mysql`.

For local development, make sure the following lines are uncommented:
```
DEBUG = TEMPLATE_DEBUG = True
```
Since Air Mozilla uses a lot of AJAX calls, it may not be useful for errors to
show up in the browser when they happen. It may be more useful to have all
the errors appear in the terminal console. This is a matter of personal
taste, but if you want all the errors to appear in the terminal add this line:
```
DEBUG_PROPAGATE_EXCEPTIONS = True
```

And, since you're probably going to run the local server NOT on HTTPS
you uncomment this line:
```
SESSION_COOKIE_SECURE = False
```
For security, you need to enter something into the `SECRET_KEY`.
```
SECRET_KEY = 'somethingnotempty'
```

By default, you need a `Memcache` server up and running. The connection
settings for that is not entered by default. So if you have a Memcache running
on the default port you need to enter it for the `LOCATION` setting like this:
```
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'KEY_PREFIX': 'airmoz',
        'TIMEOUT': 6 * 60 * 60,
        'LOCATION': 'localhost:11211'
    }
}
```

If you want to use a local in-memory cache instead, use the following
`CACHES` setting:
```
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake'
    }
}
```
By default, all the default settings are geared towards production
deployment. Not local development. For example, the default way of handling
emails is to actually send them with SMTP. For local development we don't want
this. So uncomment the line `EMAIL_BACKEND` to:
```
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
```

The majority of the remaining settings are important security details for
third-party services like AWS, Vid.ly, Mozillians, Twitter, Bit.ly and
Sentry.

Getting actual details there is a matter of trust and your relationship to the
project. Some things will obviously not work without these secrets, the file
upload for example won't work without AWS credentials. But things aren't
necessary should be something you can just go around. If something doesn't work
at all without having certain security settings, it's considered a bug.

**Step 5 - Running for the first time**

The very first thing to run are these commands:

```
./manage.py syncdb
./manage.py migrate
```
The `syncdb` command will ask you to set up a first default superuser. Make
sure you use an email address that you can log in to Persona with.

And last but not least:
```
./manage.py runserver
```

Now you should be able to open `http://localhost:8000`.

How to get it running with Docker Compose
-----------------------------------------

You need to install [Docker](http://docs.docker.com/compose/install/#install-docker)
and [Docker Compose](http://docs.docker.com/compose/install/#install-compose)
in your machine and then you can build the image, but first you have to modify
your `airmozilla/settings/local.py` file so it can connect to the database and
memcached.

```
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'postgres',
        'USER': 'postgres',
        'HOST': 'db',
        'PORT': '',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'KEY_PREFIX': 'airmoz',
        'TIMEOUT': 6 * 60 * 60,
        'LOCATION': 'memcached:11211'
    }
}
```

After this you can run the app by doing:

```
docker-compose up
```

With this the Django test server will we running, so if your are on Linux you
can connect to `localhost:8000` or to `192.168.59.103:8000` if you are on
Windows or Mac.
Due the fact that on Windows and Mac docker uses boot2docker this ip can change
at some point, to know the exact ip address you can execute `boot2docker ip`.

If you want to run regular tests you can execute:

```
docker-compose run web ./manage.py test
```

If you want to run all included selenium tests, don't forget to add
`RUN_SELENIUM_TESTS = True` and then execute:
```
docker exec -it airmozilla_web_1 ./manage.py test
```

Also if you want to ssh into the running container for debugging you should
execute:
```
docker exec -it airmozilla_web_1 bash
```

How to contribute
-----------------

There are levels of contribution. All are appreciated.

### Filing bugs

The best start you can get is to file bugs when you spot things that are broken
or could be made better. Don't be shy with filing bugs that are actually
feature requests. Your voice will always be appreciated.

[To file a bug go to this URL](https://bugzilla.mozilla.org/enter_bug.cgi?format=guided#h=dupes%7CAir+Mozilla%7COther)

### Taking bugs/Finding bugs to work on

If you [spot a bug](https://bugzilla.mozilla.org/buglist.cgi?product=Webtools&component=Air%20Mozilla&resolution=---)
that you would like to work on, you can either just get started and when you
present your patch you hope that nobody else was working on it at the same time.
Or you can post a comment on the bug saying you'd like to work on this.

An even better way would be to jump into IRC on the `#airmozilla-dev` channel
and ask around about the feature/bug you intend to work on.

We don't assign bugs to people until after the bug is resolved.

### Writing code patches

All code patches have to be submitted as GitHub Pull Requests on
https://github.com/mozilla/airmozilla.

When a pull request is made, our automation will check a couple of things:

1. **Strict PEP8 and pyflakes standards.** If your patch introduces code with
   incorrect indentation or lines too long the pull request will fail.
   This rule is there to remove any debate about how to style code as per
   how a machine likes it. It makes it non-subjective and clear.

2. All tests are run on Travis in Python 2.6. If any test fails, the pull
   request fails.

3. Test coverage regression. Test coverage is measured for every pull request
   and if you introduce a patch that has more features/changes than it has
   test coverage the test coverage percentage goes down and this doesn't
   necessarily fail the pull request but it will be less likely to be merged.

When you start working on a patch, please try to make it only about the bug
you're working on. Try to avoid fixing other things that aren't related to
the issue at hand.

Always start your work in a new git branch. **Don't start to work on the
master branch**. Before you start your branch make sure you have the most
up-to-date version of the master branch then, make a branch that ideally
has the bug number in the branch name.

Also, your git commit message should contain the bug number. If you think by
merging this patch it should resolve the bug you can add the prefix "fixes"
before the bug number.
Like this for example:

    git pull origin master
    git checkout -b bug123456789-fixing-that-thing
    ...work work work...
    git commit -a -m "fixes bug 123456789 - Fixing that thing"
    git push myforkremote bug123456789-fixing-that-thing

When you have created a pull request on GitHub, take the URL to the pull
request and post that as a comment on the bug on Bugzilla.

### Rebasing branches

Oftentimes, when you start on a branch and make a pull request you might be
asked to correct things and add more commits to it until the tests pass and
it's ready to be merged.

You might then be asked to rebase and squash your branch into a single
succinct commit. This makes it easier to look back into the commit history
when we reflect on what we've done in the year or last year.

If you're unfamiliar with rebasing, there are plenty of tutorials online but
you can also say so and we can rebase it for you manually.

### Easy does it

Any change is a good change. Getting warmed up and familiar with the code base
is best done in incremental steps. Try to start small and go through the steps
until the code has landed. The sense of accomplishment for getting your name
into the commit log history is a great boost for tackling more advanced
features or bugs.

### Code style

Consistency is key. Mixing conventions and styles makes code look
un-maintained and sticking to *one* way makes it easier to just do
instead of having to think about style choices.

For Python, all code must be PEP8 and pyflakes compliant. See the section
on **PEP8 and pyflakes**. There are some things that `flake8` can't
automatically check for. For example some choices on indentation using
newlines to split code up.

```python
# bad
channel = Channel.objects.create(name="Something",
                                 slug="something")

# ideal
channel = Channel.objects.create(
    name="Something",
    slug="something"
)
```

For Javascript, use the notation of spaced before and after brackets.

```javascript
// bad
if(number < 42){
    return 'less';
}

// ideal
if (number < 42) {
    return 'less';
}
```

For both Javascript and Python there is no rule on using single quotation
marks (`'`) or double quotation marks (`"`). But what ever the file is
using, try to stick to that.

For CSS ideally we avoid one-liners. Feel free to use plenty of space.

```css
/* bad */
.event, h2.summary{background-color:#fff;font-size:10px}

/* ideal */
.event,
h2.summary {
    background-color: #fff;
    font-size: 10px;
}
```

Getting help
------------

The best place to get help on development is to go the the `#airmozilla-dev`
IRC channel on `irc.mozilla.org`.


Tests and test coverage
-----------------------
Included is a set of comprehensive tests, which you can run by:
``./manage.py test``

If you want to run selenium tests don't forget to add
`RUN_SELENIUM_TESTS = True` in your `airmozilla/settings/local.py` file.

To see the tests' code coverage, use:
``./manage.py test --with-coverage --cover-erase --cover-html --cover-package=airmozilla``

Then, when it completes, open the file `./cover/index.html`.

You can run tests with any level of granularity:
To run a specific file, use:
``./manage.py test -s -x airmozilla/manage/tests/test_forms.py``

To run a specific test case class in a file:
``./manage.py test -s -x airmozilla/manage/tests/test_forms.py:SomeTestCaseClass``

To run a specific test in a class in a specific file:
``./manage.py test -s -x airmozilla/manage/tests/test_forms.py:SomeTestCaseClass.test_some_function``

The -s makes it so that any print statements aren't swallowed if tests pass. The -x means it bails as soon as 1 test fails.

Troubleshooting
--------------

### Deprecated Files

Make sure you don't have a `./vendor` or `./vendor-local` directory. This
functionality has been deprecated. All dependencies are now contained in the
`requirements.txt` file.

### Unable to sign in

There are several reasons why sign in might not work. A common problem is that
you have problems with CSRF and those are usually because of caching not
working. Or a security setting.

If you see this in the `runserver` logs:

```
15/Oct/201X 14:53:37] "POST /browserid/login/ HTTP/1.1" 403 2294
```

It means that the server gave you a cookie which couldn't be matched and checked
when sent back to the server later.

To check that caching works run these blocks:

```
./manage.py shell
>>> from django.core.cache import cache
>>> cache.set('some', 'thing', 60)
>>> ^D
```
(`^D` means `Ctrl-D` which means to exit the shell) then
```
./manage.py shell
>>> from django.core.cache import cache
>>> cache.get('some')
'thing'
```

If it doesn't say `'thing'` it means it wasn't able to cache things.
This is most likely because you have configured
`django.core.cache.backends.memcached.MemcachedCache` as your preferred
cache backend but that server isn't up and running.

Consider then to either figure out how to start your memcache server or switch
to `django.core.cache.backends.locmem.LocMemCache`.

Another common mistake is to *not* have `SESSION_COOKIE_SECURE = False` in your
`airmozilla/settings/local.py` but using `http://localhost:8000` to reach
the site.

### Tests are not working

If tests don't work around code you didn't touch, it might be that your test
database is out-of-sync so then next time simply run: `FORCE_DB=1 ./manage.py test`.

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

```
./manage.py migrate airmozilla.main
./manage.py migrate airmozilla.comments
./manage.py migrate airmozilla.uploads
./manage.py migrate airmozilla.subtitles
./manage.py migrate airmozilla.surveys
./manage.py migrate airmozilla.cronlogger
```

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


Logging in
----------

We use [Persona](https://login.persona.org) to handle all log in.
If you haven't used it before, it's fine. It's free and easy and works with
any email address.

Because the code is built to only allow people with certain email address
domains, (e.g. `mozilla.com`) you might need to fake this if you don't have
a `mozilla.com` email address. To do that, open the file
`airmozilla/settings/local.py` and add to the bottom this:

```
ALLOWED_BID = base.ALLOWED_BID + (
    'gmail.com',
)
```
...assuming your preferred email address is a `gmail.com` one. But note, only
enter the *domain* of your email address. Not the whole email address.

Becoming a Superuser
--------------------

Superusers have full unbound permissions to do anything and everything.

On a blank database with no content, the only way to become a Superuser
is to sign in once, then go to the command line and manually change the
data so that you're now a superuser.

```
./manage.py shell
>>> from django.contrib.auth.models import User
>>> my_user = User.objects.get(email='my@email.com')
>>> my_user.is_superuser = True
>>> my_user.is_staff = True
>>> my_user.save()
```

Adding a sample video
---------------------

Once you're a superuser, the simplest way to add sample content is to
use existing media from Air Mozilla. We're first going to create a
template, then create content based on this template.

Let's create the Video template:

 * Go to the management page at `http://localhost:8000/manage`
 * Click on `Video templates` in the left menu, and initiate a
   template with `New template`
 * Fill the `Name` with "Vid.ly"
 * Fill the `Content` with

    ```html
    <iframe frameborder="0" allowfullscreen width="896" height="504" name="vidly-frame"
     src="https://vid.ly/embeded.html?link={{ tag }}&amp;new=1&amp;autoplay={{autoplay}}&amp;hd=yes"></iframe>
    ```
 * Save changes

We're now going to initiate an event with this template:

 * Click on `Initiate event` in the left menu of the management
   page
 * Choose the `Vid.ly` template
 * Replace the Template environment with `tag=7u9u1i`
 * Change status to `Scheduled`
 * Choose a title, a description, a start time, a channel (Main) and a
   placeholder image
 * Save and submit

You should now see your video in the Event manager
(`http://localhost:8000/manage/events/`) and on the main page
(`http://localhost:8000/`)!

Contributing
------------

See CONTRIBUTING.md


IRC
---
irc://irc.mozilla.org/airmozilla-dev


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
we have to have PostgreSQL because we rely on its ability to do
fulltext index searches.


PEP8 and pyflakes
-----------------

All (with some few exceptions) code needs to be fully
[pep8](http://legacy.python.org/dev/peps/pep-0008/) and
[pyflakes](https://pypi.python.org/pypi/pyflakes) compliant. And line length
for Python is expected to be under 80 characters wide.

The help yourself enforce this automatically, you need to set up the following
git hooks. First, in your virtualenv, install this:

    pip install flake8

Next you need to create (or amend) the file:

    .git/hooks/pre-commit

...to contain the folllowing...:

```bash
#!/bin/sh

exit_code=0

for file in `git diff --cached --name-only --diff-filter=ACM | sort | uniq`
    do
        if [ ${file: -3} == ".py" ]; then
            flake8 $file
            if [ "$?" -ne "0" ]; then
                exit_code=1
            fi
        fi
        if [ ${file: -3} == ".js" ]; then
            jshint $file
            if [ "$?" -ne "0" ]; then
                exit_code=1
            fi
        fi
    done

if [ "$exit_code" -ne "0" ]; then
    echo "Aborting commit.  Fix above errors or do 'git commit --no-verify'."
    exit 1
fi
```

And make sure it's executable by running:

    chmod +x .git/hooks/pre-commit

Next time you type `git commit -a -m "fixes bug"` it might block you and spit
out a message like this instead:

```
airmozilla/main/views.py:17:1: F401 'Sum' imported but unused
airmozilla/main/views.py:378:80: E501 line too long (81 > 79 characters)
Aborting commit.  Fix above errors or do 'git commit --no-verify'.
```
