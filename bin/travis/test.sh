#!/bin/bash
# pwd is the git repo.
set -e

python manage.py test \
  --with-coverage --cover-erase --cover-package=airmozilla
