#!/bin/bash
# Run comprehensive test suite with coverage

echo "Running AI Test Solver test suite..."
echo ""

# Ensure we're in the project root
cd "$(dirname "$0")/../.."

# Activate virtual environment if it exists
if [[ -f "venv/bin/activate" ]]; then
    source venv/bin/activate
fi

# Run tests with coverage
pytest -v \
    --cov=src \
    --cov-report=term-missing \
    --cov-report=html \
    --cov-fail-under=80 \
    tests/

echo ""
echo "Test results:"
echo "- Coverage report: htmlcov/index.html"
echo "- Minimum coverage required: 80%"