# DM Helper - Quick Run Guide 🎲

A complete guide to running the DM Helper application locally with both backend and frontend services.

## 📋 Prerequisites

### Required Software
- **Node.js** (v18+): For the frontend Next.js application
- **Python** (v3.8+): For the backend FastAPI service
- **Git**: For version control (if cloning from repository)

### Installation Commands (macOS)
```bash
# Install Node.js via Homebrew
brew install node

# Install Python via Homebrew (if not already installed)
brew install python@3.11

# Verify installations
node --version    # Should show v18+
python3 --version # Should show v3.8+
npm --version     # Should show v8+
```

## 🚀 Quick Start (5 minutes)

### 1. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create virtual environment (if not exists)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt

# Start the backend server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The backend will start on **http://localhost:8000**

### 2. Frontend Setup (New Terminal)
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start the frontend development server
npm run dev
```

The frontend will start on **http://localhost:3000**

### 3. Access the Application
- **Main Interface**: http://localhost:3000
- **DM Helper Interface**: http://localhost:3000/dm
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 📁 Project Structure

```
dmhelper/
├── backend/                 # FastAPI Python backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── services/       # Business logic
│   │   └── main.py         # FastAPI application
│   ├── venv/               # Python virtual environment
│   ├── requirements.txt    # Python dependencies
│   └── M1-M6_*.md         # Implementation docs
├── frontend/               # Next.js React frontend
│   ├── src/
│   │   ├── app/           # Next.js app router
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom React hooks
│   │   └── lib/           # Utilities
│   ├── package.json       # Node.js dependencies
│   └── M6_*.md           # Implementation docs
├── data/                  # Campaign data storage
└── docker-compose.yml     # Docker setup
```

## 🔧 Detailed Setup Instructions


### Backend Configuration

1. **Environment Setup**
   ```bash
   cd backend
   
   # Copy environment template (if exists)
   cp env.example .env
   
   # Edit environment variables
   nano .env  # or your preferred editor
   ```

2. **Database Initialization** (if needed)
   ```bash
   # Create data directories
   mkdir -p data/chroma
   mkdir -p data/campaigns
   
   # Set permissions
   chmod 755 data/chroma
   ```

3. **Start Backend**
   ```bash
   # With virtual environment activated
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Frontend Configuration

1. **Environment Setup**
   ```bash
   cd frontend
   
   # Create environment file (optional)
   echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
   ```

2. **Dependency Installation**
   ```bash
   # Install all dependencies
   npm install
   
   # Or use yarn if preferred
   yarn install
   ```

3. **Start Frontend**
   ```bash
   # Development server
   npm run dev
   
   # Or production build + start
   npm run build
   npm start
   ```

## 🎯 Using the Application

### Initial Setup

1. **Index Knowledge Base**
   - Go to http://localhost:3000/dm
   - Click on "Sources" tab
   - The system will automatically index any documents in `data/campaigns/`

2. **Add Campaign Documents**
   ```bash
   # Add your campaign files to
   mkdir -p data/campaigns/rules
   mkdir -p data/campaigns/lore
   mkdir -p data/campaigns/characters
   
   # Copy your PDFs, markdown files, etc.
   cp your_rulebook.pdf data/campaigns/rules/
   cp campaign_notes.md data/campaigns/lore/
   ```

### Key Features

**Chat Interface**
- Navigate to the "Chat" tab
- Ask questions like:
  - "What is the armor class calculation?"
  - "Tell me about magic missiles"
  - "How do I create a level 5 fighter?"

**Search Interface** 
- Use the "Search" tab for direct knowledge base queries
- Filter by sources and relevance scores
- View complete citation information

**Source Management**
- Check indexing status in "Sources" tab
- View document statistics
- Monitor knowledge base health

## 🐛 Troubleshooting

### Common Issues

**Backend Won't Start**
```bash
# Check Python version
python3 --version

# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Check for port conflicts
lsof -i :8000
```

**Frontend Won't Start**
```bash
# Check Node.js version
node --version

# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install

# Check for port conflicts  
lsof -i :3000
```

**API Connection Issues**
```bash
# Test backend health
curl http://localhost:8000/api/v1/health

# Check CORS settings in backend
# Verify NEXT_PUBLIC_API_URL in frontend/.env.local
```

**Knowledge Base Issues**
```bash
# Check data directory permissions
ls -la data/

# Manually trigger indexing
curl -X POST http://localhost:8000/api/v1/knowledge/index

# Clear and rebuild index
curl -X DELETE http://localhost:8000/api/v1/knowledge/index
curl -X POST http://localhost:8000/api/v1/knowledge/index
```

### Port Configuration

**Change Default Ports**
```bash
# Backend (different port)
uvicorn app.main:app --host 0.0.0.0 --port 8080

# Frontend (different port)
npm run dev -- --port 3001

# Update frontend environment
echo "NEXT_PUBLIC_API_URL=http://localhost:8080" > frontend/.env.local
```

## 🐳 Docker Alternative

**Quick Docker Setup**
```bash
# Start both services with Docker
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 📊 Verification Steps

### Health Checks

1. **Backend Health**
   ```bash
   curl http://localhost:8000/api/v1/health
   # Should return: {"status": "healthy", ...}
   ```

2. **Frontend Access**
   - Visit: http://localhost:3000
   - Should see DM Helper landing page

3. **API Integration**
   - Go to: http://localhost:3000/dm
   - Check that knowledge base stats load
   - Try a search query

4. **Full Workflow Test**
   - Add a document to `data/campaigns/rules/`
   - Index via API or Sources tab
   - Search for content from the document
   - Verify citations appear correctly

## 🔧 Development Commands

### Backend
```bash
cd backend
source venv/bin/activate

# Run tests
python -m pytest

# Format code
black app/

# Type checking
mypy app/

# Start with debug
uvicorn app.main:app --reload --log-level debug
```

### Frontend
```bash
cd frontend

# Run linting
npm run lint

# Type checking
npm run type-check

# Build for production
npm run build

# Run tests (when added)
npm test
```

## 📚 Next Steps

After getting the application running:

1. **Add Campaign Data**: Copy your D&D documents to `data/campaigns/`
2. **Explore Features**: Try chat, search, and character creation
3. **Customize**: Modify components in `frontend/src/components/`
4. **Extend**: Add new API endpoints in `backend/app/api/endpoints/`

## 🆘 Getting Help

**Check Implementation Status**:
- Backend: See `backend/M*_IMPLEMENTATION_COMPLETE.md` files
- Frontend: See `frontend/M6_IMPLEMENTATION_COMPLETE.md`

**Common File Locations**:
- Backend logs: Terminal where uvicorn is running
- Frontend logs: Browser developer console
- API documentation: http://localhost:8000/docs
- Configuration: `backend/.env` and `frontend/.env.local`

---

**🎉 You're Ready!** Your DM Helper should now be running at http://localhost:3000/dm

For advanced configuration and deployment options, see the individual milestone documentation files. 