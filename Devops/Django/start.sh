#!/bin/sh

python manage.py makemigrations authentication chat remote_auth friends game

python manage.py migrate

exec "$@"
