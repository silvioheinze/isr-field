#!/bin/bash
set -e

# Fix permissions for mounted volumes
if [ -d "/usr/src/app/staticfiles" ]; then
    chown -R appuser:appuser /usr/src/app/staticfiles
fi

if [ -d "/usr/src/app/media" ]; then
    chown -R appuser:appuser /usr/src/app/media
fi

# Run Django commands
python manage.py collectstatic --noinput --clear
python manage.py migrate

# Start the application
exec "$@"