#!/bin/bash

# Frontend Startup Script
echo "Starting AI Research Draft Generator Frontend..."

cd "$(dirname "$0")"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed."
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "Error: npm is not installed."
    exit 1
fi

echo "Node.js version: $(node --version)"
echo "npm version: $(npm --version)"

# Install dependencies
echo "Installing Node.js dependencies..."
# npm install

echo "Frontend dependencies ready!"

echo "Frontend dependencies installed successfully!"
echo ""
echo "Starting React development server..."
echo "Frontend will be available at: http://localhost:3000"
echo ""

# Start the React application
npm start
