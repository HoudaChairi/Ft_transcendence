#!/bin/sh

python manage.py makemigrations authentication chat remote_auth friends

python manage.py migrate

exec "$@"
