#!/bin/bash

# Pharmacy API Webservice Deployment Script
# This script helps deploy the API to production

echo "🚀 Deploying Pharmacy API Webservice..."

# Check if we're in the right directory
if [ ! -f "pharma_api/app/main.py" ]; then
    echo "❌ Error: Please run this script from the pharmacy_ingest root directory"
    exit 1
fi

# Check if .env file exists
if [ ! -f "pharma_api/.env" ]; then
    echo "⚠️  Warning: .env file not found. Please create one from .env.example"
    echo "   cp pharma_api/.env.example pharma_api/.env"
    echo "   Then edit with your production database credentials and API key"
fi

# Install/update dependencies
echo "📦 Installing dependencies..."
cd pharma_api
pip install -r requirements.txt

# Check if database is accessible
echo "🔍 Testing database connection..."
python -c "
from app.db import get_conn
try:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT 1')
            print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Database connection failed. Please check your .env configuration"
    exit 1
fi

# Start the service
echo "🌟 Starting Pharmacy API Webservice..."
echo "   Service will be available at: http://localhost:8000"
echo "   API Documentation: http://localhost:8000/docs"
echo "   Health Check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the service"
echo ""

# Start uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 