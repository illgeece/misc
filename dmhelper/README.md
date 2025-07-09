# DM Helper - AI  Companion

An intelligent assistant for Dungeon Masters that combines conversational AI with specialized D&D tools and knowledge management. My first foray into AI agent coding. Works, but too huge and messy to try and fix and improve. 
No longer in use. 
## Features

- **Conversational AI**: Natural language Q&A about rules, lore, NPCs, and items
- **Knowledge Management**: Automatically indexes and searches your campaign documents
- **Character Creation**: Template-based character generation with validation
- **Dice Engine**: Inline dice rolling with deterministic results
- **File System Integration**: Monitors campaign folders for changes
- **Citation System**: All AI answers include source references

## Architecture

```
┌─────────────────┐
│   Web / UI      │  React / Next.js (desktop + mobile)
└──────┬──────────┘
       │ REST / WebSocket
┌──────▼──────────┐
│  API Gateway    │  FastAPI (Python)
└──────┬──────────┘
       │
┌──────▼──────────┐
│  Orchestrator   │  Handles chat session, tool routing
└─┬────┬────┬─────┘
  │    │    │
  │    │    │
  │    │    └── Character Service
  │    └──────── Knowledge Service (vector store)
  └───────────── Dice / Rules Engine
```

## Project Structure

```
dmhelper/
├── backend/                 # Python FastAPI backend
│   ├── app/
│   │   ├── core/           # Core utilities and config
│   │   ├── services/       # Business logic services
│   │   ├── api/            # REST API endpoints
│   │   ├── models/         # Data models
│   │   └── main.py         # FastAPI application
│   ├── tests/              # Backend tests
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile          # Backend container
├── frontend/               # React/Next.js frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/          # Next.js pages
│   │   ├── hooks/          # Custom React hooks
│   │   ├── lib/            # Utility functions
│   │   └── types/          # TypeScript types
│   ├── tests/              # Frontend tests
│   ├── package.json        # Node dependencies
│   └── Dockerfile          # Frontend container
├── docs/                   # Documentation
├── docker-compose.yml      # Development environment
└── README.md              # This file
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (optional)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd dmhelper
   ```

2. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   ```

4. **Environment Configuration**
   ```bash
   # Copy example environment files
   cp backend/.env.example backend/.env
   cp frontend/.env.example frontend/.env
   # Edit the .env files with your configuration
   ```

### Running the Application

#### Option 1: Docker Compose (Recommended)
```bash
docker-compose up --build
```

#### Option 2: Manual Development
```bash
# Terminal 1 - Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### Access Points

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Campaign Folder Structure

The application expects a campaign folder with this structure:

```
campaign_root/
├── rules/               # PDFs, markdown, txt files
├── lore/                # World documents
├── characters/
│   ├── templates/       # *.yaml character templates
│   └── pcs/             # Generated *.json player characters
└── sessions/
    ├── 2025-01-08.md   # Session notes
    └── ...
```

## Development

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test

# E2E tests
npm run test:e2e
```

### Code Quality

```bash
# Backend linting and formatting
cd backend
black app/ tests/
flake8 app/ tests/
mypy app/

# Frontend linting and formatting
cd frontend
npm run lint
npm run format
```

## Technology Stack

- **Backend**: Python, FastAPI, Pydantic, SQLAlchemy
- **Frontend**: React, Next.js, TypeScript, Tailwind CSS
- **AI/ML**: OpenAI GPT-4, Chroma (vector database)
- **Document Processing**: Unstructured.io, pdfplumber
- **Real-time**: WebSocket, Server-Sent Events
- **Testing**: pytest, Jest, Playwright
- **DevOps**: Docker, Docker Compose

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

MIT License - see LICENSE file for details 
