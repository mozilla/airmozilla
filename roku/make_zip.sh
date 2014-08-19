#!/bin/bash
set -e

python check_url_prefix.py airmozilla/source/categoryFeed.brs
rm -f airmozilla.zip
find . | grep --color=never '\~$' | xargs rm -f
find . | grep '\.DS_Store' | xargs rm -fr
find . | grep '\.versions' | xargs rm -fr
find . | grep '\.versions' | xargs rmdir
pushd airmozilla
zip -9 -r ../airmozilla.zip .
popd
echo "Created airmozilla.zip"
