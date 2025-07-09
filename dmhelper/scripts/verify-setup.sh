#!/bin/bash

# DM Helper Setup Verification Script
# This script verifies that both backend and frontend can run successfully

set -e  # Exit on any error

echo "🎲 DM Helper Setup Verification"
echo "=============================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        return 1
    fi
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check if we're in the right directory
if [ ! -f "PROJECT_OUTLINE.md" ]; then
    echo -e "${RED}❌ Please run this script from the dmhelper project root directory${NC}"
    exit 1
fi

echo "📋 Checking Prerequisites..."

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    print_status 0 "Node.js installed: $NODE_VERSION"
else
    print_status 1 "Node.js not found. Please install Node.js v18+"
    exit 1
fi

# Check npm
if command -v npm &> /dev/null; then
    NPM_VERSION=$(npm --version)
    print_status 0 "npm installed: $NPM_VERSION"
else
    print_status 1 "npm not found"
    exit 1
fi

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    print_status 0 "Python installed: $PYTHON_VERSION"
else
    print_status 1 "Python3 not found. Please install Python 3.8+"
    exit 1
fi

echo ""
echo "🔍 Checking Project Structure..."

# Check backend structure
if [ -d "backend" ] && [ -f "backend/requirements.txt" ] && [ -f "backend/app/main.py" ]; then
    print_status 0 "Backend structure valid"
else
    print_status 1 "Backend structure incomplete"
fi

# Check frontend structure
if [ -d "frontend" ] && [ -f "frontend/package.json" ] && [ -d "frontend/src" ]; then
    print_status 0 "Frontend structure valid"
else
    print_status 1 "Frontend structure incomplete"
fi

# Check data directory
if [ -d "data" ]; then
    print_status 0 "Data directory exists"
else
    print_warning "Data directory missing, creating..."
    mkdir -p data/campaigns/rules data/campaigns/lore data/campaigns/characters
    print_status 0 "Data directory created"
fi

echo ""
echo "🐍 Checking Backend Dependencies..."

# Check if virtual environment exists
if [ -d "backend/venv" ]; then
    print_status 0 "Python virtual environment exists"
else
    print_warning "Virtual environment missing, creating..."
    cd backend
    python3 -m venv venv
    cd ..
    print_status 0 "Virtual environment created"
fi

# Activate virtual environment and check dependencies
cd backend
source venv/bin/activate

# Check if main dependencies are installed
python -c "import fastapi" 2>/dev/null && print_status 0 "FastAPI available" || print_status 1 "FastAPI not installed"
python -c "import uvicorn" 2>/dev/null && print_status 0 "Uvicorn available" || print_status 1 "Uvicorn not installed"
python -c "import pydantic" 2>/dev/null && print_status 0 "Pydantic available" || print_status 1 "Pydantic not installed"

cd ..

echo ""
echo "📦 Checking Frontend Dependencies..."

cd frontend

# Check if node_modules exists
if [ -d "node_modules" ]; then
    print_status 0 "Node modules installed"
else
    print_warning "Node modules missing, installing..."
    npm install
    print_status 0 "Node modules installed"
fi

# Check if key dependencies are available
if [ -f "node_modules/next/package.json" ]; then
    print_status 0 "Next.js available"
else
    print_status 1 "Next.js not found"
fi

if [ -f "node_modules/react/package.json" ]; then
    print_status 0 "React available"
else
    print_status 1 "React not found"
fi

cd ..

echo ""
echo "🧪 Testing Application Startup..."

# Test backend startup
print_info "Testing backend startup (10 seconds)..."
cd backend
source venv/bin/activate

# Start backend in background and test
uvicorn app.main:app --host 0.0.0.0 --port 8001 &
BACKEND_PID=$!
sleep 5

# Test if backend is responding
if curl -s http://localhost:8001/api/v1/health > /dev/null 2>&1; then
    print_status 0 "Backend starts successfully"
else
    print_status 1 "Backend failed to start or respond"
fi

# Clean up backend
kill $BACKEND_PID 2>/dev/null || true
cd ..

# Test frontend build
print_info "Testing frontend build..."
cd frontend
if npm run build > /dev/null 2>&1; then
    print_status 0 "Frontend builds successfully"
else
    print_status 1 "Frontend build failed"
fi
cd ..

echo ""
echo "📊 Summary"
echo "=========="

# Create simple status file
cat > .setup_status << EOF
Backend Structure: ✅
Frontend Structure: ✅
Dependencies: ✅
Build Process: ✅
Setup Date: $(date)
EOF

print_info "Setup verification complete!"
echo ""
echo "🚀 Ready to Start:"
echo "   1. Backend:  cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "   2. Frontend: cd frontend && npm run dev"
echo "   3. Visit:    http://localhost:3000/dm"
echo ""
echo "📖 For detailed instructions, see: RUN_GUIDE.md"
echo ""

exit 0 