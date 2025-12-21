#!/bin/bash
set -e

echo "Waiting for MySQL to be ready..."
# MySQL이 준비될 때까지 대기
while ! nc -z $MYSQL_HOST $MYSQL_PORT; do
  sleep 1
done
echo "MySQL is ready!"

echo "Initializing database..."
python init_db.py

echo "Starting application..."
exec "$@"
