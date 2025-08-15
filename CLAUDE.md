# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI Test Solver FastAPI project that provides intelligent test solving capabilities with OCR, RAG (Retrieval-Augmented Generation), and concurrent processing. The project uses modern Python packaging with pyproject.toml and follows FastAPI best practices for scalable API development.

## Development Commands

### Environment Management
- `python -m venv venv` - Create virtual environment
- `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows) - Activate virtual environment
- `deactivate` - Deactivate virtual environment
- `pip install -e ".[dev]"` - Install project with development dependencies
- `pip install -e .` - Install project in development mode (production dependencies only)

### FastAPI Development Commands
- `uvicorn src.ai_test_solver.main:app --reload --host 0.0.0.0 --port 8000` - Start development server
- `uvicorn src.ai_test_solver.main:app --host 0.0.0.0 --port 8000` - Start production server
- `python -m src.ai_test_solver.main` - Run application directly

### Package Management
- `pip install <package>` - Install a package
- `python -m build` - Build distribution packages
- `pip check` - Verify package dependencies

### Testing Commands
- `pytest` - Run all tests
- `pytest -v` - Run tests with verbose output
- `pytest --cov` - Run tests with coverage report
- `pytest --cov-report=html` - Generate HTML coverage report
- `pytest -x` - Stop on first failure
- `pytest -k "test_name"` - Run specific test by name
- `python -m unittest` - Run tests with unittest

### Code Quality Commands
- `black src/ tests/` - Format code with Black
- `black --check src/ tests/` - Check code formatting without changes
- `ruff check src/ tests/` - Run linting with Ruff
- `ruff check --fix src/ tests/` - Fix auto-fixable linting issues
- `mypy src/` - Run type checking with MyPy
- `ruff check src/ tests/ && black --check src/ tests/ && mypy src/` - Run all quality checks

### Development Tools
- `python -m pip install --upgrade pip` - Upgrade pip
- `python -c "import sys; print(sys.version)"` - Check Python version
- `python -m site` - Show Python site information
- `python -m pdb script.py` - Debug with pdb

## Technology Stack

### Core Technologies
- **Python 3.11+** - Primary programming language
- **FastAPI** - Modern async web framework with automatic OpenAPI documentation
- **Pydantic** - Data validation and settings management using Python type hints
- **Uvicorn** - Lightning-fast ASGI server

### Project-Specific Technologies
- **Supabase** - Backend-as-a-Service with PostgreSQL database
- **Redis** - In-memory data structure store for caching
- **AsyncPG** - Async PostgreSQL database driver
- **Google Cloud Vision** - OCR and image analysis
- **Google Cloud Storage** - Object storage for files
- **OpenAI** - Language model integration
- **Sentence Transformers** - Embedding generation for RAG

### Data Science & ML
- **NumPy** - Numerical computing
- **Pandas** - Data manipulation and analysis
- **Matplotlib/Seaborn** - Data visualization
- **Scikit-learn** - Machine learning library
- **TensorFlow/PyTorch** - Deep learning frameworks

### Testing Frameworks
- **pytest** - Testing framework
- **unittest** - Built-in testing framework
- **pytest-cov** - Coverage plugin for pytest
- **factory-boy** - Test fixtures
- **responses** - Mock HTTP requests

### Code Quality Tools
- **Black** - Uncompromising code formatter
- **Ruff** - Extremely fast Python linter (replaces flake8, isort, and more)
- **MyPy** - Static type checker
- **pytest** - Testing framework with async support
- **pytest-cov** - Coverage reporting for pytest

## Project Structure Guidelines

### File Organization
```
src/
├── ai_test_solver/
│   ├── __init__.py
│   ├── main.py          # FastAPI application entry point
│   ├── api/             # API endpoints and routers
│   │   ├── __init__.py
│   │   ├── health.py    # Health check endpoints
│   │   └── tests.py     # Test processing endpoints
│   ├── core/            # Core configuration and utilities
│   │   ├── __init__.py
│   │   ├── config.py    # Settings and configuration
│   │   ├── exceptions.py # Custom exceptions
│   │   └── logging.py   # Logging configuration
│   ├── models/          # Pydantic models and database schemas
│   │   ├── __init__.py
│   │   ├── api.py       # API request/response models
│   │   ├── knowledge.py # Knowledge base models
│   │   └── test.py      # Test-related models
│   ├── services/        # Business logic and external integrations
│   │   ├── __init__.py
│   │   ├── database.py  # Database service
│   │   ├── embedding.py # Vector embedding service
│   │   ├── llm.py       # LLM integration
│   │   ├── ocr.py       # OCR processing
│   │   └── rag.py       # RAG implementation
│   └── utils/           # Utility functions
tests/
├── __init__.py
├── conftest.py          # pytest configuration and fixtures
├── integration/         # Integration tests
├── unit/               # Unit tests
└── test_health.py      # Health endpoint tests
pyproject.toml          # Project configuration and dependencies
sql/                    # Database migrations and sample data
├── migrations/
└── sample_data.sql
```

### Naming Conventions
- **Files/Modules**: Use snake_case (`user_profile.py`)
- **Classes**: Use PascalCase (`UserProfile`)
- **Functions/Variables**: Use snake_case (`get_user_data`)
- **Constants**: Use UPPER_SNAKE_CASE (`API_BASE_URL`)
- **Private methods**: Prefix with underscore (`_private_method`)

## Python Guidelines

### Type Hints
- Use type hints for function parameters and return values
- Import types from `typing` module when needed
- Use `Optional` for nullable values
- Use `Union` for multiple possible types
- Document complex types with comments

### Code Style
- Follow PEP 8 style guide
- Use meaningful variable and function names
- Keep functions focused and single-purpose
- Use docstrings for modules, classes, and functions
- Limit line length to 88 characters (Black default)

### Best Practices
- Use list comprehensions for simple transformations
- Prefer `pathlib` over `os.path` for file operations
- Use context managers (`with` statements) for resource management
- Handle exceptions appropriately with try/except blocks
- Use `logging` module instead of print statements

## Testing Standards

### Test Structure
- Organize tests to mirror source code structure
- Use descriptive test names that explain the behavior
- Follow AAA pattern (Arrange, Act, Assert)
- Use fixtures for common test data
- Group related tests in classes

### Coverage Goals
- Aim for 90%+ test coverage
- Write unit tests for business logic
- Use integration tests for external dependencies
- Mock external services in tests
- Test error conditions and edge cases

### pytest Configuration
```python
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--cov=src --cov-report=term-missing"
```

## Virtual Environment Setup

### Creation and Activation
```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Dependencies Management
- Use `pyproject.toml` for all dependency management
- Main dependencies defined in `project.dependencies`
- Development dependencies in `project.optional-dependencies.dev`
- Use `pip install -e ".[dev]"` to install with dev dependencies

## FastAPI-Specific Guidelines

### API Design Patterns
- Use versioned API routes (`/api/v1/`)
- Implement proper HTTP status codes
- Use Pydantic models for request/response validation
- Leverage FastAPI's automatic OpenAPI documentation
- Implement proper error handling with custom exceptions

### Async Programming
- Use `async def` for all route handlers that perform I/O
- Use `await` for database operations, HTTP requests, and file I/O
- Leverage asyncio for concurrent processing
- Use dependency injection for shared resources

### Configuration Management
- Use Pydantic Settings for configuration
- Environment-based configuration with `.env` files
- Separate settings for development, testing, and production
- Never commit secrets to version control

### Database Integration
- Use async database drivers (asyncpg for PostgreSQL)
- Implement proper connection pooling
- Use dependency injection for database sessions
- Handle database migrations with SQL files

## Security Guidelines

### Dependencies
- Regularly update dependencies with `pip list --outdated`
- Use `safety` package to check for known vulnerabilities
- Pin dependency versions in requirements files
- Use virtual environments to isolate dependencies

### Code Security
- Validate input data with Pydantic or similar
- Use environment variables for sensitive configuration
- Implement proper authentication and authorization
- Sanitize data before database operations
- Use HTTPS for production deployments

## Development Workflow

### Before Starting
1. Check Python version compatibility
2. Create and activate virtual environment
3. Install dependencies from requirements files
4. Run type checking with `mypy`

### During Development
1. Use type hints for better code documentation
2. Run tests frequently to catch issues early
3. Use meaningful commit messages
4. Format code with Black before committing

### Before Committing
1. Run full test suite: `pytest -v --cov=src --cov-report=term-missing`
2. Check code formatting: `black --check src/ tests/`
3. Run linting: `ruff check src/ tests/`
4. Run type checking: `mypy src/`
5. Verify no print statements: Use logger instead of print()

### Quick Quality Check
Run all quality checks in sequence:
```bash
ruff check src/ tests/ && black --check src/ tests/ && mypy src/ && pytest
```