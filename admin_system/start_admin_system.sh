#!/bin/bash

# GDTA 2026 Admin System - Quick Setup Script
# This script sets up and starts the admin registration system

echo "========================================"
echo "GDTA 2026 Admin System Setup"
echo "========================================"
echo ""

# Navigate to chatbot directory
cd "$(dirname "$0")"

# Check if Python is installed
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "❌ Python is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Use python3 if available, otherwise python
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
else
    PYTHON_CMD=python
fi

echo "✓ Using Python: $PYTHON_CMD"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

echo ""

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate || . venv/Scripts/activate

echo "✓ Virtual environment activated"
echo ""

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✓ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo ""

# Initialize database
echo "🗄️  Initializing database..."
$PYTHON_CMD -c "from db.models import init_db, create_default_admin; init_db(); create_default_admin()"

if [ $? -eq 0 ]; then
    echo "✓ Database initialized successfully"
else
    echo "⚠️  Database may already exist (this is okay)"
fi

echo ""
echo "========================================"
echo "✅ Setup Complete!"
echo "========================================"
echo ""
echo "🚀 Starting server..."
echo ""
echo "Access points:"
echo "  📱 Chatbot Registration: http://localhost:5000/register"
echo "  🎛️  Admin Dashboard: http://localhost:5000/admin"
echo ""
echo "Default admin credentials:"
echo "  👤 Username: admin"
echo "  🔑 Password: admin123"
echo ""
echo "⚠️  IMPORTANT: Change the default password in production!"
echo ""
echo "Press Ctrl+C to stop the server"
echo "========================================"
echo ""

# Start the Flask server
$PYTHON_CMD app.py
