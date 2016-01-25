#!/bin/bash
# pwd is the git repo.
set -e

echo "Install latestish pip"
pip install -U "pip>=8.0.0"

echo "Install Python dependencies"
pip install --require-hashes -r requirements.txt
# less important requirements
pip install -r dev-requirements.txt

echo "Creating a test database"
psql -c 'create database airmozilla;' -U postgres
