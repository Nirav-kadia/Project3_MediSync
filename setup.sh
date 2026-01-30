#!/bin/bash

# MediSync Setup Script

echo "🏥 Setting up MediSync - GraphRAG Patient Intelligence Platform"
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cat > .env << EOF
# MediSync Environment Configuration

# Google ADK / Gemini API
GOOGLE_API_KEY=your_google_api_key_here

# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=medisync123

# Phoenix Telemetry (optional)
PHOENIX_ENABLED=true
PHOENIX_ENDPOINT=http://localhost:6006/v1/traces

# Application Settings
APP_ENV=development
APP_PORT=5001
EOF
    echo "⚠️  Please update .env with your actual API keys!"
fi

# Create data directories
echo "Creating data directories..."
mkdir -p data/ontologies

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Update .env with your GOOGLE_API_KEY"
echo "2. Start Neo4j: docker-compose up -d"
echo "3. Run the app: source venv/bin/activate && python app/main.py"
echo ""

