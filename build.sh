#!/usr/bin/env bash

# =============================================
# build.sh - Render.com build script
# =============================================

set -o errexit

echo "Starting Render build process..."

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Fix database schema (add missing columns)
echo "Fixing database schema..."
python fix_database.py

echo "Build complete!"