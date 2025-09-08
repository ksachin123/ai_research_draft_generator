#!/bin/bash

# Backend Startup Script
echo "Starting AI Research Draft Generator Backend..."

cd "$(dirname "$0")"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Set environment variables
export FLASK_APP=app
export FLASK_ENV=development
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Create necessary directories
mkdir -p data/documents
mkdir -p data/chromadb
mkdir -p logs

echo "Backend environment setup complete!"
echo ""
echo "Starting Flask development server..."
echo "API will be available at: http://localhost:5001"
echo "Swagger documentation at: http://localhost:5001/swagger/"
echo ""

# Start the Flask application on port 5001 to avoid conflicts with AirPlay
flask run --port=5001
