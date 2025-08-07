#!/bin/bash

# ISR Field Production Deployment Script
# This script helps deploy the ISR Field application using Docker

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}ISR Field Production Deployment${NC}"
echo "=================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found. Creating template...${NC}"
    cat > .env << EOF
# Database Configuration
POSTGRES_DB=isrfield
POSTGRES_USER=isruser
POSTGRES_PASSWORD=isrpassword

# Django Configuration
DJANGO_SECRET_KEY=your-secret-key-here
DEBUG=False

# GitHub Repository (replace with your actual repository)
GITHUB_REPOSITORY=your-username/isr-field
EOF
    echo -e "${YELLOW}Please edit .env file with your actual values before continuing.${NC}"
    exit 1
fi

# Load environment variables
source .env

# Check if required variables are set
if [ -z "$DJANGO_SECRET_KEY" ] || [ "$DJANGO_SECRET_KEY" = "your-secret-key-here" ]; then
    echo -e "${RED}Error: Please set DJANGO_SECRET_KEY in .env file${NC}"
    exit 1
fi

if [ -z "$GITHUB_REPOSITORY" ] || [ "$GITHUB_REPOSITORY" = "your-username/isr-field" ]; then
    echo -e "${RED}Error: Please set GITHUB_REPOSITORY in .env file${NC}"
    exit 1
fi

echo -e "${GREEN}Configuration loaded successfully${NC}"

# Pull latest images
echo -e "${YELLOW}Pulling latest Docker images...${NC}"
docker-compose -f docker-compose.prod.yml pull

# Stop existing containers
echo -e "${YELLOW}Stopping existing containers...${NC}"
docker-compose -f docker-compose.prod.yml down

# Start services
echo -e "${YELLOW}Starting services...${NC}"
docker-compose -f docker-compose.prod.yml up -d

# Wait for database to be ready
echo -e "${YELLOW}Waiting for database to be ready...${NC}"
sleep 10

# Run migrations
echo -e "${YELLOW}Running database migrations...${NC}"
docker-compose -f docker-compose.prod.yml exec app python manage.py migrate

# Create superuser if it doesn't exist
echo -e "${YELLOW}Checking for superuser...${NC}"
if ! docker-compose -f docker-compose.prod.yml exec app python manage.py shell -c "from django.contrib.auth.models import User; User.objects.filter(is_superuser=True).exists()" 2>/dev/null | grep -q "True"; then
    echo -e "${YELLOW}No superuser found. You can create one with:${NC}"
    echo "docker-compose -f docker-compose.prod.yml exec app python manage.py createsuperuser"
fi

# Check health
echo -e "${YELLOW}Checking application health...${NC}"
sleep 5
if curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
    echo -e "${GREEN}Application is healthy!${NC}"
    echo -e "${GREEN}Access your application at: http://localhost:8000${NC}"
else
    echo -e "${RED}Health check failed. Check logs with:${NC}"
    echo "docker-compose -f docker-compose.prod.yml logs app"
fi

echo -e "${GREEN}Deployment completed!${NC}"
