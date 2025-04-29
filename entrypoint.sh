#!/bin/sh

# Function to check if postgres is ready
postgres_ready() {
python << END
import sys
import psycopg2
try:
    psycopg2.connect(
        dbname="${DB_NAME:-postgres}",
        user="${DB_USER:-postgres}",
        password="${DB_PASSWORD:-password}",
        host="${DB_HOST:-postgres-service}",
        port="${DB_PORT:-5432}",
    )
except psycopg2.OperationalError:
    sys.exit(-1)
sys.exit(0)
END
}

## Apply database migrations
echo "Applying database migrations..."
python manage.py migrate

## Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start Gunicorn
echo "Starting Gunicorn..."
exec gunicorn faceit_proj.wsgi:application \
    --bind 0.0.0.0:8001 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
