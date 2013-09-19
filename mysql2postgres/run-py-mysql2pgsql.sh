#!/bin/bash

# optional
#virtualenv tmpvenv
#source tmpvenv/bin/activate


#pip install py-mysql2pgsql

PYTHONPATH=./py-mysql2pgsql-0.1.5 python ./py-mysql2pgsql-0.1.5/bin/py-mysql2pgsql


echo ""
echo "This should have created a file called mysql2pgsql.yml"
echo "Edit that file. It should be obvious how it works."
echo ""
echo "When you're done, run:"
echo "py-mysql2pgsql -v -f mysql2pgsql.yml"
