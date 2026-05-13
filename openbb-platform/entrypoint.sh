#!/bin/sh
set -eu

python /app/seed_credentials.py

exec openbb-api "$@"
