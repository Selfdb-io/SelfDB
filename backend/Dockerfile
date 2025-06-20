# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Set environment variables to prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies if needed (e.g., for psycopg2 build)
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev curl && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# Copy only requirements.txt first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
# Ensure .dockerignore prevents copying unnecessary files (like .git, .venv)
COPY ./app /app/app

# Copy Alembic migrations
COPY ./alembic /app/alembic
COPY ./alembic.ini /app/alembic.ini

# Copy initialization scripts
COPY ./scripts /app/scripts
RUN chmod +x /app/scripts/init.sh

# Expose the port the app runs on
# Note: The actual port mapping to the host is done in docker-compose.yml
EXPOSE 8000

# Command to run the application using Uvicorn
# --host 0.0.0.0 makes the server accessible from outside the container network
# --reload enables auto-reloading on code changes (useful for development)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Alternative command for initialization and then running the app
# CMD ["/bin/bash", "-c", "/app/scripts/init.sh && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]
