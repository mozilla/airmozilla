#!/bin/bash
# pwd is the git repo.
set -e

echo "Install Python dependencies"
pip install --no-deps -r requirements.txt
pip install --no-deps -r dev-requirements.txt

# install the same stuff with peep (slow)
pip install bin/peep-2.4.1.tar.gz
peep install -r requirements.txt

echo "Creating a test database"
psql -c 'create database airmozilla;' -U postgres
