# Base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Build argument to differentiate dev/prod
ARG ENV=dev
ENV ENV=${ENV}

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install dev dependencies only in dev environment
RUN if [ "$ENV" = "dev" ]; then \
        pip install --no-cache-dir -r requirements-dev.txt; \
    fi

# Copy project files
COPY . .

# Collect static files only in production
RUN if [ "$ENV" = "prod" ]; then \
        python manage.py collectstatic --noinput; \
    fi

# Expose default Django port
EXPOSE 8000

# Run migrations and start server
CMD if [ "$ENV" = "prod" ]; then \
        python manage.py migrate && \
        gunicorn myproject.wsgi:application --bind 0.0.0.0:8000; \
    else \
        python manage.py migrate && \
        python manage.py runserver 0.0.0.0:8000; \
    fi
