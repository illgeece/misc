#!/bin/bash

# Setup script for Ollama with Gemma 4B model for DM Helper

set -e

echo "🚀 Setting up Ollama for DM Helper..."

# Check if Ollama is already installed
if command -v ollama &> /dev/null; then
    echo "✅ Ollama is already installed"
else
    echo "📦 Installing Ollama..."
    
    # Install Ollama based on OS
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install ollama
        else
            echo "Please install Homebrew first or download Ollama from https://ollama.ai"
            exit 1
        fi
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        curl -fsSL https://ollama.ai/install.sh | sh
    else
        echo "Unsupported OS. Please install Ollama manually from https://ollama.ai"
        exit 1
    fi
fi

# Start Ollama service
echo "🔧 Starting Ollama service..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to start
echo "⏳ Waiting for Ollama to start..."
sleep 5

# Function to check if Ollama is ready
check_ollama() {
    curl -s http://localhost:11434/api/tags > /dev/null 2>&1
}

# Wait for Ollama to be ready
for i in {1..30}; do
    if check_ollama; then
        echo "✅ Ollama is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Ollama failed to start after 30 seconds"
        exit 1
    fi
    sleep 1
done

# Check if Gemma 4B model is already available
echo "🔍 Checking for Gemma 4B model..."
if ollama list | grep -q "gemma2:4b"; then
    echo "✅ Gemma 4B model is already available"
else
    echo "📥 Pulling Gemma 4B model (this may take a few minutes)..."
    ollama pull gemma2:4b
    echo "✅ Gemma 4B model downloaded successfully"
fi

# Test the model
echo "🧪 Testing Gemma 4B model..."
TEST_RESPONSE=$(ollama run gemma2:4b "Hello, can you help with D&D?" --format json 2>/dev/null || echo "")

if [[ -n "$TEST_RESPONSE" ]]; then
    echo "✅ Gemma 4B model is working correctly"
else
    echo "⚠️  Model test had issues, but installation appears complete"
fi

# Stop the background Ollama process if we started it
if [[ -n "$OLLAMA_PID" ]]; then
    kill $OLLAMA_PID 2>/dev/null || true
fi

echo ""
echo "🎉 Ollama setup complete!"
echo ""
echo "Next steps:"
echo "1. Start Ollama: ollama serve"
echo "2. In another terminal, start the DM Helper backend"
echo "3. The application will automatically use the Gemma 4B model"
echo ""
echo "Model info:"
echo "  - Model: gemma2:4b"
echo "  - API URL: http://localhost:11434" 
echo "  - Memory usage: ~2.5GB"
echo ""
echo "To start Ollama as a service:"
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "  brew services start ollama"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "  sudo systemctl enable ollama"
    echo "  sudo systemctl start ollama"
fi 