#!/bin/bash
set -e

# Wait for the database to be ready
echo "Waiting for database to be ready..."
python -c "
import time
import psycopg2
import os

host = os.environ.get('POSTGRES_SERVER', 'postgres')
user = os.environ.get('POSTGRES_USER', 'selfdb_user')
password = os.environ.get('POSTGRES_PASSWORD', 'selfdb_password')
dbname = os.environ.get('POSTGRES_DB', 'selfdb')

while True:
    try:
        conn = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            dbname=dbname
        )
        conn.close()
        break
    except psycopg2.OperationalError:
        print('Database not ready yet, waiting...')
        time.sleep(1)
"

# Run migrations
echo "Running database migrations..."
cd /app && alembic upgrade head

# Create initial data
echo "Creating initial data..."
cd /app && python -m app.initial_data

echo "Initialization complete!"
