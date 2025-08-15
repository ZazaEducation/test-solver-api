#!/bin/bash
# Run all code quality checks

echo "Running code quality checks for AI Test Solver..."
echo ""

# Ensure we're in the project root
cd "$(dirname "$0")/../.."

# Activate virtual environment if it exists
if [[ -f "venv/bin/activate" ]]; then
    source venv/bin/activate
fi

# Track overall exit status
OVERALL_EXIT=0

echo "🔍 Running Ruff linter..."
if ! ruff check src/ tests/; then
    echo "❌ Ruff linting failed"
    OVERALL_EXIT=1
else
    echo "✅ Ruff linting passed"
fi
echo ""

echo "🎨 Checking code formatting with Black..."
if ! black --check --diff src/ tests/; then
    echo "❌ Code formatting check failed"
    echo "💡 Run: black src/ tests/ to fix formatting"
    OVERALL_EXIT=1
else
    echo "✅ Code formatting check passed"
fi
echo ""

echo "🔬 Running MyPy type checking..."
if ! mypy src/; then
    echo "❌ Type checking failed"
    OVERALL_EXIT=1
else
    echo "✅ Type checking passed"
fi
echo ""

if [[ $OVERALL_EXIT -eq 0 ]]; then
    echo "🎉 All code quality checks passed!"
else
    echo "❌ Some code quality checks failed. Please fix the issues above."
fi

exit $OVERALL_EXIT