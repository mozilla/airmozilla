#!/bin/bash

/usr/bin/Xvfb :99 -ac -screen 0 1280x1024x16 >/dev/null 2>/dev/null &

echo "Executing './manage.py syncdb --no-input'"
./manage.py syncdb --noinput
echo "Executing './manage.py migrate'"
./manage.py migrate
echo "Executing './manage.py runserver 0.0.0.0:8000'"
./manage.py runserver 0.0.0.0:8000

exec "$@"
