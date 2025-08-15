#!/bin/bash
# Clean up build artifacts and temporary files

echo "Cleaning up AI Test Solver project..."
echo ""

# Ensure we're in the project root
cd "$(dirname "$0")/../.."

# Remove build artifacts
echo "🧹 Removing build artifacts..."
rm -rf build/
rm -rf dist/
rm -rf *.egg-info/

# Remove Python cache files
echo "🗑️ Removing Python cache files..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete

# Remove test artifacts
echo "📊 Removing test artifacts..."
rm -rf .pytest_cache/
rm -rf .coverage
rm -rf htmlcov/

# Remove type checking cache
echo "🔬 Removing MyPy cache..."
rm -rf .mypy_cache/

# Remove other temporary files
echo "🧽 Removing other temporary files..."
rm -rf .ruff_cache/
rm -rf .tox/

echo ""
echo "✅ Cleanup complete!"
echo ""
echo "Removed:"
echo "- Build artifacts (build/, dist/, *.egg-info/)"
echo "- Python cache files (__pycache__/, *.pyc, *.pyo)"
echo "- Test artifacts (.pytest_cache/, .coverage, htmlcov/)"
echo "- Type checking cache (.mypy_cache/)"
echo "- Linter cache (.ruff_cache/)"