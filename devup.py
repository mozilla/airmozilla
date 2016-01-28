#!/usr/bin/env python

import os
import sys
import subprocess
import re


def _proceed(msg="Ready to proceed?"):
    ready = raw_input(msg + ' [Y/n]: ').lower().strip()
    if ready in ('n', 'no'):
        raise SystemExit("Ok. Leaving the guide.")
    else:
        print "\n"


def _error(msg):
    for line in msg.splitlines():
        print "\t", line.lstrip()
    raise SystemExit("Exiting the guide now.")


def _process(command, shell=False):
    if isinstance(command, basestring):
        command = command.split()
    assert isinstance(command, list)
    p = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=shell
    )
    return p.communicate()


def _process_streamed(command):
    if isinstance(command, basestring):
        command = command.split()
    assert isinstance(command, list)
    # print "COMMAND\t", command
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    for c in iter(lambda: process.stdout.read(1), ''):
        sys.stdout.write(c)


def welcome():
    print """

    WELCOME TO THE AIR MOZILLA DEVELOPMENT ENVIRONMENT SETTER UPPER

    This guide will help you get a working dev environment on your
    laptop so you can work on Air Mozilla code.

    What this guide simply does is automate the documented steps in
    the README at
    https://github.com/mozilla/airmozilla/#how-to-get-it-running-locally-from-scratch

    """
    _proceed()


def check_python_version():
    # it must be python 2.7
    if sys.version_info >= (2, 7) and sys.version_info < (3,):
        print "Great! You have Python", sys.version.split()[0], "installed."
        _proceed()
    else:
        _error("""
        Sorry. Can't continue.

        You have Python %s installed and running this guide.
        It needs to be Python 2.7.

        Either go and install one of those and try again or if you already
        actually have it installed, try to start this guide with it
        differently.
        """ % sys.version.split()[0])


def _get_virtualenv_version():
    try:
        output, error = _process('virtualenv --version')
        return output.strip().split()[-1]
    except OSError:
        return None


def check_virtualenv():
    virtualenv_version = _get_virtualenv_version()
    if virtualenv_version:
        print (
            "Great you have virtualenv %s installed!" % virtualenv_version
        )
        _proceed()
    else:
        _error("""Problem!

        You don't have virtualenv installed. Try installing it into your
        system python with:

        sudo pip install virtualenv

        """)


def _in_virtualenv():
    return hasattr(sys, 'real_prefix')


def _get_git_version():
    try:
        output, error = _process('git --version')
        return output.strip().split()[-1]
    except OSError:
        return None


def check_git():

    git_version = _get_git_version()
    if git_version:
        print "Great! You have git", git_version, "installed."
        _proceed()
    else:
        _error("""
        It appears you do not have git installed.

        Depending on your system you have to install that yourself.
        """)


def _get_psql_version():
    try:
        output, error = _process(['psql', '--version'])
        return re.search(r"[0-9.].*", output.strip()).group()
    except OSError:
        return None


def check_psql():

    psql_version = _get_psql_version()
    if psql_version:
        if not psql_version.startswith('9'):
            _error("""
            psql version not starting with 9 (%r).

            You need to have PostgreSQL version 9.x installed.
            """ % psql_version)
        else:
            print "Great! psql is installed."
            _proceed()
    else:
        _error("""
        Unable to get a version of `psql`.

        PostgreSQL appear to be be installed! It's needed.
        """)


def create_database():
    print "Now we're going to create a PostgreSQL database"
    database_name = raw_input("Name of the database: [airmozilla] ").strip()
    database_name = database_name or 'airmozilla'

    # does it already exist?
    out, err = _process("psql -l")
    lines = out.splitlines()[3:-2]
    names = [x.split()[0] for x in lines]
    if database_name in names:
        _error("""Problem!

        There is already a database called %s
        """ % database_name)

    command = "createdb -E UTF8 %s" % database_name
    out, err = _process(command)
    if err:
        _error("""Problem!

        Unable to create the database with the command:
        %s

        Error:
        %s
        """ % (command, err))
    else:
        print "Great! Database created."
        _proceed()

    return database_name


def in_git_cloned_already():
    output, error = _process(['git', 'status'])
    return not (error and not output)


def _norm_path(path):
    return os.path.abspath(
        os.path.normpath(
            os.path.expanduser(path)
        )
    )


def git_clone():
    print "Going to git clone the whole project"
    print "Where do you want to clone the project too?"
    _here = _norm_path('.')
    print "Default is the current directory"
    destination = raw_input('Path [%s/airmozilla]: ' % _here)
    destination = _norm_path(destination)
    if not destination.endswith('airmozilla'):
        if not os.path.isdir(destination):
            _error("%s is not an directory that exists" % destination)
        destination = os.path.join(destination, 'airmozilla')
    else:
        # e.g. they entered /some/path
        if os.path.isdir(destination):
            destination = os.path.join(destination, 'airmozilla')
        else:
            _error("%s is not an directory that exists" % destination)

    _process_streamed(
        [
            'git', 'clone',
            'https://github.com/mozilla/airmozilla.git',
            destination
        ]
    )
    print ""
    print "Yay! All the code has been clone. Now let's configure things"
    _proceed()
    return destination


def create_virtualenv(repo_root):
    if _in_virtualenv() and os.environ.get('VIRTUAL_ENV'):
        virtualenv_path = os.environ['VIRTUAL_ENV']
        virtualenv_name = os.path.basename(virtualenv_path)
        print (
            "You are currently in an activated virtualenv called %s" %
            virtualenv_name
        )
        use_that = raw_input(
            "Use the current virtualenv? [Y/n] "
        ).strip().lower()
        use_that = use_that not in ('n', 'no')
        if use_that:
            _proceed()
            return virtualenv_path

    print (
        "NOTE! If you already have and know how to use mkvirtualenv "
        "you have to create a virtualenv and install the dependencies "
        "on your own."
    )
    use_mkvenv = raw_input(
        "Run mkvirtualenv commands yourself? [y/N] "
    ).lower().strip()
    use_mkvenv = use_mkvenv in ('y', 'yes')
    if use_mkvenv:
        print "These are the commands you need to run:"
        print
        print "\tmkvirtualenv airmozilla"
        print "\tpip install -r %s/requirements.txt" % repo_root
        print
        print "You can do that once the other things are set up"
        return

    virtualenv_path = raw_input(
        "Path to the virtualenv [default: airmozilla/.virtualenv] "
    ).strip()
    virtualenv_path = virtualenv_path or 'airmozilla/.virtualenv'
    virtualenv_path = _norm_path(virtualenv_path)
    _process_streamed('virtualenv %s' % virtualenv_path)
    return virtualenv_path


def install_python_dependencies(repo_root, virtualenv_name):
    # then virtualenv_name is a path
    print
    print (
        "Now we're going to attempt to install all the\n"
        "dependencies. Let's hope it works. If not, you might\n"
        "have to attempt this manually. The command we're going"
        " to use is:\n"
        'pip install -r %s/requirements.txt' % (
            repo_root,
        )
    )

    _process_streamed(
        '%s/bin/pip install -r %s/requirements.txt' % (
            virtualenv_name,
            repo_root
        )
    )
    print "Great! Python dependencies installed."
    _proceed()


def install_node_dependencies(repo_root):
    print
    print (
        "Now we're going to install the Node dependencies.\n"
        "This assumes you have a working version of npm.\n"
        "The command we're going to use is:\n"
        "npm install"
    )
    _process_streamed(
        'npm install'
    )
    print "Great! Node dependencies installed."
    _proceed()


def install_python_dev_dependencies(repo_root, virtualenv_name):
    # then virtualenv_name is a path
    print
    print (
        "Now we're going to attempt to install all the\n"
        "dev dependencies. Let's hope it works. If not, you might\n"
        "have to attempt this manually. The command we're going"
        " to use is:\n"
        'pip install -r %s/dev-requirements.txt' % (
            repo_root,
        )
    )

    _process_streamed(
        '%s/bin/pip install -r %s/dev-requirements.txt' % (
            virtualenv_name,
            repo_root
        )
    )
    print "Great! Python dev dependencies installed."
    _proceed()


def create_local_settings(repo_root, database_name):
    template_path = os.path.join(
        repo_root,
        'airmozilla',
        'settings',
        'local.py-dist'
    )
    assert os.path.isfile(template_path), template_path
    template = open(template_path).read()
    destination_path = template_path.replace('-dist', '')
    template = template.replace(
        "'NAME': 'airmozilla',",
        "'NAME': '%s'," % database_name
    )
    template = template.replace(
        '#DEBUG = TEMPLATE_DEBUG = True',
        'DEBUG = TEMPLATE_DEBUG = True'
    )
    template = template.replace(
        '#SESSION_COOKIE_SECURE = False',
        'SESSION_COOKIE_SECURE = False'
    )
    template = template.replace(
        "SECRET_KEY = ''",
        "SECRET_KEY = 'anything'"
    )
    template = template.replace(
        "#EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'",
        "EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'"
    )
    template = template.replace(
        """#CACHES = {
#    'default': {
#        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
#        'LOCATION': 'unique-snowflake'
#    }
#}""",
        """CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake'
    }
}"""
    )

    open(destination_path, 'w').write(template)
    print (
        "We have now created a local settings file (%s) which "
        "is a file you're free to edit and change." %
        destination_path
    )

    _proceed()


def about_first_migration(repo_root, venv_path):
    print """Now you should have a virtualenv and all things installed.

    The next thing to do is to run the first migrations. Go into the
    project:

    \tcd %s
    """ % repo_root

    if venv_path:
        print "Activate your virtualenv. E.g.:"
        print ""
        print "\tsource %s/bin/activate" % (
            venv_path.replace(repo_root + '/', ''),
        )
        print
    else:

        print "Activate your virtualenv."
        print

    print """Now you should be able to run:

    \t./manage.py syncdb
    \t./manage.py migrate

        """


def run():
    welcome()

    check_python_version()

    check_virtualenv()

    check_git()

    check_psql()

    database_name = create_database()

    if in_git_cloned_already():
        repo_root = _norm_path('.')
    else:
        repo_root = git_clone()

    create_local_settings(repo_root, database_name)

    venv_path = create_virtualenv(repo_root)
    install_python_dependencies(repo_root, venv_path)
    install_python_dev_dependencies(repo_root, venv_path)
    install_node_dependencies(repo_root)

    about_first_migration(repo_root, venv_path)

    print "ALL IS DONE!"
    print "Good luck hacking. See you in #airmozilla-dev"
    print
    return 0


if __name__ == '__main__':
    sys.exit(run())
