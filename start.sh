#!/bin/bash

echo "🚀 Starting PDF Processing Microservice..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ .env file not found! Creating from example..."
    cp env_example.txt .env
    echo "✅ .env file created. Please edit it with your API keys."
    echo "Then run this script again."
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Start the service
echo "🌟 Starting microservice on http://localhost:8000"
python main.py 