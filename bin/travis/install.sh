#!/bin/bash
# pwd is the git repo.
set -e

echo "Install latestish pip"
python bin/pipstrap.py

echo "Install Python dependencies"
pip install --quiet --require-hashes -r requirements.txt
# less important requirements
pip install --quiet -r dev-requirements.txt

echo "Creating a test database"
psql -c 'create database airmozilla;' -U postgres
