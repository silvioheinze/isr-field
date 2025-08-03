FROM python:3.13-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gdal-bin \
        libgdal-dev \
        python3-dev \
        gcc \
        build-essential \
        libpq-dev \
        libgeos-dev \
        proj-bin \
        proj-data \
        libproj-dev \
        libxml2-dev \
        libxslt-dev \
        libffi-dev \
        zlib1g-dev \
        libjpeg-dev \
        tzdata \
        gettext \
    && rm -rf /var/lib/apt/lists/*

# Set timezone
ENV TZ=Europe/Vienna

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /usr/src/app

# Install dependencies
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY ./app/ .