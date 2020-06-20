#!/usr/bin/env bash


set -o errexit
set -o pipefail
set -o nounset
set -o xtrace

python /app/manage.py migrate --noinput
# python /app/manage.py collectstatic --clear --noinput

python manage.py runserver --noreload --nothreading 0.0.0.0:8000
