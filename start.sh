#!/bin/bash
# Quick start script for Utah Campaign Finance app

set -e  # Exit on error

echo "🚀 Utah Campaign Finance Disclosures - Quick Start"
echo "=================================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q -r requirements.txt

# Check if database exists
if [ ! -f "db.sqlite3" ]; then
    echo "🗄️  Setting up database..."
    python3 manage.py makemigrations
    python3 manage.py migrate

    echo ""
    echo "👤 Create an admin user (you can do this later with: python3 manage.py createsuperuser)"
    read -p "Create admin user now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python3 manage.py createsuperuser
    fi

    echo ""
    echo "📊 Import sample data? This will import report #198820 for testing."
    read -p "Import sample report? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python3 manage.py import_disclosure https://disclosures.utah.gov/Search/PublicSearch/Report/198820
    fi
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "🌐 Starting development server..."
echo "   Visit: http://localhost:8000/"
echo "   Admin: http://localhost:8000/admin/"
echo ""
echo "   Press Ctrl+C to stop the server"
echo ""

python3 manage.py runserver
