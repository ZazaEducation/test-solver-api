#!/bin/bash
# Start FastAPI development server with hot reload

echo "Starting AI Test Solver API in development mode..."
echo "Server will be available at: http://localhost:8000"
echo "API documentation at: http://localhost:8000/docs"
echo ""

# Ensure we're in the project root
cd "$(dirname "$0")/../.."

# Activate virtual environment if it exists
if [[ -f "venv/bin/activate" ]]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Start the development server
uvicorn src.ai_test_solver.main:app \
    --reload \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info