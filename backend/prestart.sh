#! /usr/bin/env bash

python /app/census_api/backend_pre_start.py
alembic upgrade head
