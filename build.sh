#!/usr/bin/env bash

# =============================================
# build.sh - Render.com build script
# This runs automatically during deployment
# =============================================

set -o errexit

echo "Starting Render build process..."

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations (will skip if no migrations folder exists)
echo "Running database migrations..."
flask db upgrade || echo "No migrations to apply"

# Create tables if they don't exist
echo "Ensuring database tables exist..."
python -c "from app import app, db, init_database; init_database()"

echo "Build complete!"