#!/bin/bash
# Format code and fix auto-fixable linting issues

echo "Formatting AI Test Solver code..."
echo ""

# Ensure we're in the project root
cd "$(dirname "$0")/../.."

# Activate virtual environment if it exists
if [[ -f "venv/bin/activate" ]]; then
    source venv/bin/activate
fi

echo "🎨 Formatting code with Black..."
black src/ tests/
echo ""

echo "🔧 Fixing auto-fixable issues with Ruff..."
ruff check --fix src/ tests/
echo ""

echo "✅ Code formatting complete!"
echo "💡 Run './claude/commands/lint.sh' to verify all checks pass"