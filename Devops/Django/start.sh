#!/bin/sh

python manage.py makemigrations authentication chat remote_auth two_factor

python manage.py migrate

exec "$@"
