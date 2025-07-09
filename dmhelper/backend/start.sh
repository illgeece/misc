#!/bin/bash
# Start script for DM Helper backend

# Navigate to backend directory
cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Set Python path to current directory so 'app' module can be found
export PYTHONPATH=$(pwd)

# Override paths to use project root relative paths
export CHROMA_PERSIST_DIRECTORY="../data/chroma"
export CAMPAIGN_ROOT_DIR="../data/campaigns"

# Start the backend server using python -m for better module resolution
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload 
