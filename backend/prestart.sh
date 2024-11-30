#! /usr/bin/env bash

set -e
set -x

python /app/census_api/backend_pre_start.py
alembic upgrade head
