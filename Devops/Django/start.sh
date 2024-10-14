#!/bin/sh

python manage.py makemigrations authentication chat

python manage.py migrate

exec "$@"
