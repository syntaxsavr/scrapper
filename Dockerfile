# Base image
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
COPY requirements-dev.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

ARG ENVIRONMENT=development
RUN if [ "$ENVIRONMENT" = "development" ]; then \
        pip install -r requirements-dev.txt; \
    fi

COPY . .

RUN if [ "$ENVIRONMENT" = "production" ]; then \
        python manage.py collectstatic --noinput; \
    fi

    

EXPOSE 8000
