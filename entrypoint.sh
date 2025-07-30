#!/bin/bash

# Exit on any error
set -e

echo "Starting Django Webhook Inspector deployment setup..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
while ! pg_isready -h ${POSTGRES_HOST:-localhost} -p ${POSTGRES_PORT:-5432} -U ${POSTGRES_USER:-postgres}
do
  echo "Waiting for PostgreSQL..."
  sleep 2
done
echo "PostgreSQL is ready!"

# Wait for Redis to be ready
echo "Waiting for Redis to be ready..."
while ! redis-cli -h ${REDIS_HOST:-localhost} -p ${REDIS_PORT:-6379} ping
do
  echo "Waiting for Redis..."
  sleep 2
done
echo "Redis is ready!"

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt

# Run database migrations
echo "Running database migrations..."
python manage.py makemigrations
python manage.py migrate

# Create superuser if it doesn't exist
echo "Creating superuser if needed..."
python manage.py shell << EOF
from django.contrib.auth import get_user_model
from django.conf import settings
import os

User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Superuser '{username}' created successfully!")
else:
    print(f"Superuser '{username}' already exists.")
EOF

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run tests (optional - can be disabled for faster deployment)
if [ "${RUN_TESTS:-false}" = "true" ]; then
    echo "Running tests..."
    python manage.py test
fi

echo "Django setup completed successfully!"

# Start the application based on the environment
if [ "${ENVIRONMENT:-development}" = "production" ]; then
    echo "Starting production server..."
    exec gunicorn webhook_inspector.wsgi:application -c gunicorn.conf.py
else
    echo "Starting development server..."
    exec python manage.py runserver 0.0.0.0:8000
fi
