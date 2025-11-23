#!/bin/bash
# Start the SALESBOT Training System Backend

echo "🚀 Starting SALESBOT Training System Backend..."
echo ""
echo "The backend will be available at: http://localhost:8080"
echo "API Documentation: http://localhost:8080/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

cd "$(dirname "$0")"
python main.py
