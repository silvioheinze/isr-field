#!/bin/bash

# Test script for production Docker build
set -e

echo "Testing production Docker build..."

# Build the production image
echo "Building production image..."
docker build -f Dockerfile.prod -t test-isr-field-prod .

# Test Django import
echo "Testing Django import..."
docker run --rm test-isr-field-prod python -c "import django; print('✓ Django import successful')"

# Test health check endpoint (without database)
echo "Testing health check endpoint..."
docker run --rm -d --name test-health test-isr-field-prod
sleep 5
if docker exec test-health curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
    echo "✓ Health check endpoint working"
else
    echo "✗ Health check endpoint failed"
fi

# Cleanup
docker stop test-health
docker rmi test-isr-field-prod

echo "Production build test completed successfully!"
