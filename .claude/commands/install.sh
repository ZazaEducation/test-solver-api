#!/bin/bash
# Setup development environment for AI Test Solver

echo "Setting up AI Test Solver development environment..."
echo ""

# Ensure we're in the project root
cd "$(dirname "$0")/../.."

# Check Python version
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"

# Check if we meet minimum requirements (3.11+)
if ! python -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
    echo "❌ Python 3.11+ is required. Current version: $PYTHON_VERSION"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [[ ! -d "venv" ]]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install project with development dependencies
echo "📋 Installing project with development dependencies..."
pip install -e ".[dev]"

# Verify installation
echo ""
echo "🔍 Verifying installation..."
echo "FastAPI version: $(python -c 'import fastapi; print(fastapi.__version__)')"
echo "Pytest version: $(python -c 'import pytest; print(pytest.__version__)')"
echo "Black version: $(python -c 'import black; print(black.__version__)')"
echo "Ruff version: $(ruff --version)"

echo ""
echo "✅ Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Start development server: ./.claude/commands/dev.sh"
echo "3. Run tests: ./.claude/commands/test.sh"