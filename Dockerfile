# Base Python Image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=faceit_proj.settings

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    netcat-openbsd \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Need to have a folder for staticfiles
RUN mkdir -p /app/staticfiles

# Give entrypoint executable permission
RUN chmod +x /app/entrypoint.sh

# Expose port
EXPOSE 8001

# Start Gunicorn server
ENTRYPOINT ["/app/entrypoint.sh"]
