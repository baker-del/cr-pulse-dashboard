#!/bin/bash

# KPI Dashboard Quick Start Script

echo "🚀 Starting KPI Dashboard Setup..."
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null
then
    echo "❌ Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"
echo ""

# Check if dependencies are installed
if ! python3 -c "import streamlit" &> /dev/null; then
    echo "📦 Installing dependencies..."
    pip3 install -r requirements.txt
    echo "✅ Dependencies installed"
    echo ""
fi

# Check if database exists
if [ ! -f "database/kpi_dashboard.db" ]; then
    echo "🔧 Initializing database..."
    python3 database/init_db.py
    echo ""
fi

# Start the application
echo "🎉 Launching KPI Dashboard..."
echo ""
echo "The app will open in your browser at: http://localhost:8501"
echo ""
echo "To access from other computers on your network:"
echo "1. Find your IP address with: ifconfig | grep 'inet '"
echo "2. Share http://YOUR_IP:8501 with your team"
echo ""
echo "Press Ctrl+C to stop the server"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

streamlit run app.py
