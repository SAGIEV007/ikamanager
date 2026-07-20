#!/bin/bash
# IkaManager - Quick Start Script
# Run this script to start the application

set -e

echo "======================================"
echo "  IkaManager - Starting..."
echo "======================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed!"
    echo ""
    echo "Please install Docker Desktop:"
    echo "  Windows: https://docs.docker.com/desktop/install/windows-install/"
    echo "  Mac:     https://docs.docker.com/desktop/install/mac-install/"
    echo "  Linux:   https://docs.docker.com/desktop/install/linux-install/"
    echo ""
    exit 1
fi

# Check if docker compose is available
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
else
    echo "ERROR: Docker Compose is not installed!"
    exit 1
fi

echo "Building and starting services..."
echo ""

$COMPOSE_CMD up --build -d

echo ""
echo "======================================"
echo "  IkaManager is running!"
echo ""
echo "  Open in your browser:"
echo "  http://localhost:3000"
echo ""
echo "  To stop: $COMPOSE_CMD down"
echo "======================================"
