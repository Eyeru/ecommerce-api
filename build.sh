#!/usr/bin/env bash
set -o errexit

echo "BUILD SCRIPT RUNNING"

pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate