#!/bin/sh

python manage.py makemigrations authentication chat remote_auth

python manage.py migrate

exec "$@"
