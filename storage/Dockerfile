FROM python:3.13-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the main.py file
COPY main.py .

# Set Python path
ENV PYTHONPATH=/app

# Create data directory
RUN mkdir -p /app/data

# Run the application (port from environment)
CMD ["python", "main.py"]