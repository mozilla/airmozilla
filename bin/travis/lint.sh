#!/bin/sh
flake8 airmozilla --exclude=*/migrations/*,airmozilla/settings/*.py,airmozilla/base/akamai_token_v2.py
