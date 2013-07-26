#!/bin/bash

virtualenv tmpvenv
source tmpvenv/bin/activate
pip install py-mysql2pgsql
py-mysql2pgsql

echo ""
echo "This should have created a file called mysql2pgsql.yml"
echo "Edit that file. It should be obvious how it works."
echo ""
echo "When you're done, run:"
echo "py-mysql2pgsql -v -f mysql2pgsql.yml"
