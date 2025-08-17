# Sleep Consultation AI - API Application

This folder contains all API-related components for the Sleep Consultation AI system.

## Structure

```
app/
├── __init__.py          # Package initialization
├── main.py              # Main entry point for the API
├── api.py               # FastAPI application with all endpoints
├── database.py          # Database models and operations
├── schemas.py           # Pydantic schemas for API requests/responses
└── README.md           # This documentation
```

## Running the API

### Option 1: Using main.py
```bash
python app/main.py
```

### Option 2: Using uvicorn directly
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Option 3: Using Python module
```bash
python -m app.main
```

## API Endpoints

### Health Check
- `GET /api/health` - Service health status and monitoring

### Referral Letter Processing
- `POST /api/referral-letter` - Upload PDF and get auth token

### Chat System
- `POST /api/chat` - Chat with auth token

### Data Retrieval
- `GET /api/consultations/search` - Search and filter consultations
- `GET /api/consultations/{id}` - Get consultation details
- `GET /api/statistics` - Get system statistics

## Database

The API uses SQLite with SQLAlchemy ORM. Database file: `sleep_consultation.db`

## Authentication

Uses secure auth tokens generated when uploading referral letters. Tokens are single-use and become invalid after consultation completion.

## File Storage

PDF files are stored in the `stored_pdfs/` directory with timestamp-based naming.