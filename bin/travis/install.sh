#!/bin/bash
# pwd is the git repo.
set -e

echo "Install peep"
pip install bin/peep-2.4.1.tar.gz

echo "Install Python dependencies"
peep install -r requirements.txt
# less important requirements
pip install -r dev-requirements.txt

echo "Creating a test database"
psql -c 'create database airmozilla;' -U postgres
