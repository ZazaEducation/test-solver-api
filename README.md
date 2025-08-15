# AI Test Solver API

An intelligent test solving API that processes PDF and image files containing test questions, extracts questions using OCR, and provides AI-generated answers using RAG (Retrieval-Augmented Generation) with vector search.

## Features

- **Universal Test Processing**: Handles any test format (PDFs, images)
- **Intelligent Question Extraction**: Automatic question detection and classification
- **Multi-Type Question Support**: Multiple choice, short answer, essay, true/false, fill-in-blank
- **RAG-Powered Solving**: Combines curated knowledge base with real-time web search
- **Concurrent Processing**: Processes multiple questions simultaneously for speed
- **5-minute SLA**: Complete processing within 5 minutes
- **Confidence Scoring**: AI provides confidence levels and detailed explanations

## Tech Stack

- **Backend**: FastAPI with async/await
- **Database**: Supabase (PostgreSQL + pgvector)
- **OCR**: Google Cloud Vision API
- **LLM**: OpenAI GPT-4o-mini
- **Search**: Google Custom Search API
- **Vector Search**: Sentence Transformers + pgvector
- **Deployment**: Google Cloud Run
- **Caching**: Redis for performance optimization

## API Endpoints

### POST /api/v1/tests/upload
Upload a test file (PDF or image) for processing.

### GET /api/v1/tests/{test_id}
Retrieve test results and processing status.

### GET /api/v1/tests/{test_id}/status
Check processing status of a test.

### GET /api/v1/health
Health check endpoint.

## Quick Start

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd ai-test-solver
   ```

2. **Install dependencies**:
   ```bash
   pip install -e .
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

4. **Run the application**:
   ```bash
   uvicorn src.ai_test_solver.main:app --reload
   ```

## Environment Variables

```env
# Database
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key

# Google Cloud
GOOGLE_CLOUD_PROJECT=your_project_id
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
GOOGLE_CUSTOM_SEARCH_API_KEY=your_search_api_key
GOOGLE_CUSTOM_SEARCH_ENGINE_ID=your_search_engine_id

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Redis (optional)
REDIS_URL=redis://localhost:6379

# Application
API_SECRET_KEY=your_secret_key
DEBUG=false
```

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black src/ tests/
ruff check src/ tests/
```

### Type Checking
```bash
mypy src/
```

## Deployment

Deploy to Google Cloud Run:

```bash
gcloud run deploy ai-test-solver \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "ENVIRONMENT=production"
```

## License

MIT License - see LICENSE file for details.# test-solver-api
