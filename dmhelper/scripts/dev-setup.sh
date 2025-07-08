#!/bin/bash

# DM Helper - Development Setup Script
set -e

echo "🎯 Setting up DM Helper development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null && ! command -v docker compose &> /dev/null; then
    print_error "Docker Compose is not available. Please install Docker Compose."
    exit 1
fi

print_status "Docker is available"

# Check for required environment variables
if [ ! -f "backend/.env" ]; then
    print_warning "Creating backend/.env from template..."
    cp backend/env.example backend/.env
    print_warning "Please edit backend/.env with your OpenAI API key and other settings"
fi

if [ ! -f "frontend/.env.local" ]; then
    print_warning "Creating frontend/.env.local..."
    cat > frontend/.env.local << EOF
NEXT_PUBLIC_API_URL=http://localhost:8000
EOF
fi

# Create data directories
print_status "Creating data directories..."
mkdir -p data/campaigns/{rules,lore,characters/{templates,pcs},sessions}
mkdir -p backend/data/{chroma,campaigns}

# Set up Python virtual environment for local development
if [ ! -d "backend/venv" ]; then
    print_status "Creating Python virtual environment..."
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    cd ..
fi

print_status "Development environment setup complete!"

echo ""
echo "🚀 To start the application:"
echo "   Option 1 (Docker): docker-compose up --build"
echo "   Option 2 (Manual): "
echo "     - Backend: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "     - Frontend: cd frontend && npm install && npm run dev"
echo ""
echo "📝 Don't forget to:"
echo "   - Set your OpenAI API key in backend/.env"
echo "   - Add your campaign documents to data/campaigns/"
echo ""
echo "🌐 Application URLs:"
echo "   - Frontend: http://localhost:3000"
echo "   - Backend API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs" 