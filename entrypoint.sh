#!/bin/bash
set -e

# Fix permissions for mounted volumes (as root)
if [ -d "/usr/src/app/staticfiles" ]; then
    chown -R appuser:appuser /usr/src/app/staticfiles
fi

if [ -d "/usr/src/app/media" ]; then
    chown -R appuser:appuser /usr/src/app/media
fi

# Switch to appuser and run Django commands
python manage.py collectstatic --noinput
python manage.py migrate

exec "$@"