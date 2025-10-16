# PO Search & Parsing System - Implementation Plan

## Architecture Overview

**Backend**: FastAPI + SQLite (metadata cache) + Google APIs + Tesseract OCR + OpenAI GPT-4  
**Frontend**: React + TailwindCSS + modern chat UI  
**Flow**: User query → GPT-4 interprets → Backend searches Gmail/Drive → Parse PO → Return structured data

## Project Structure

```
po-project/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Environment vars & settings
│   │   ├── models.py            # SQLAlchemy models for metadata
│   │   ├── database.py          # DB connection & session
│   │   ├── routers/
│   │   │   ├── search.py        # Search endpoints
│   │   │   └── chat.py          # GPT-4 chat interface
│   │   ├── services/
│   │   │   ├── gmail_service.py      # Gmail API integration
│   │   │   ├── drive_service.py      # Drive API integration
│   │   │   ├── parser_service.py     # PO parsing (PDF/Word/OCR)
│   │   │   ├── gpt_service.py        # GPT-4 query interpretation
│   │   │   └── search_service.py     # Fuzzy search logic
│   │   └── utils/
│   │       ├── auth.py          # Google OAuth helper
│   │       └── extractors.py   # Regex patterns for PO data
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInterface.jsx
│   │   │   ├── SearchBar.jsx
│   │   │   └── POResultCard.jsx
│   │   ├── services/
│   │   │   └── api.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── index.html
└── README.md
```

## Implementation Steps

### Phase 1: Backend Foundation

#### 1. FastAPI Setup
- Initialize FastAPI project with CORS middleware
- Create `config.py` with settings: `GOOGLE_CLIENT_ID`, `OPENAI_API_KEY`, `DATABASE_URL`
- Set up SQLite database with SQLAlchemy
- Create PO metadata model: `id`, `po_number`, `date`, `client_name`, `total_value`, `source` (gmail/drive), `file_id`, `filename`, `parsed_data` (JSON), `created_at`

#### 2. Google OAuth & API Integration
- Implement OAuth 2.0 flow in `utils/auth.py` using `google-auth-oauthlib`
- Store credentials in `token.json` for local development
- Create `gmail_service.py`: Search attachments via Gmail API (`messages.list` + `messages.get` with parts)
- Create `drive_service.py`: Search files via Drive API (`files.list` with query builder)
- Both services return: `file_id`, `filename`, `source`, `download_url`

#### 3. Document Parsing Engine
- `parser_service.py` handles multiple formats:
  - **PDF (text-based)**: Use `PyPDF2` or `pdfplumber` for text extraction
  - **PDF (scanned)**: Use `pytesseract` + `pdf2image` for OCR
  - **Word docs**: Use `python-docx` for .docx parsing
- Extract key fields using `extractors.py`:
  - PO number: regex `(?:PO|P\.O\.|Purchase Order)[:\s#]*([A-Z0-9-]+)`
  - Date: `dateutil.parser` for flexible date parsing
  - Client/Buyer: Look for "Buyer:", "Client:", "Vendor:" sections
  - Line items: Table extraction (coordinates or text parsing)
  - Payment terms: regex for "NET 30", "Payment Terms:", etc.
- Return structured dict: `{po_number, date, client, items[], total_value, terms}`

#### 4. Intelligent Search Service
- `search_service.py` implements multi-stage search:
  1. **Metadata search**: Query SQLite cache with fuzzy matching (using `fuzzywuzzy`)
  2. **Gmail search**: If cache miss, search Gmail with query like `filename:(PO OR "purchase order") {user_query}`
  3. **Drive search**: Search Drive with `fullText contains '{query}' and mimeType contains 'pdf|word'`
  4. Combine results, deduplicate by file hash/ID
  5. Parse new documents and cache metadata
- Endpoint: `POST /api/search` → returns list of PO summaries

### Phase 2: GPT-4 Chat Interface

#### 5. GPT-4 Query Interpretation
- `gpt_service.py` uses OpenAI API with function calling
- System prompt: "You help users find purchase orders. Convert natural language queries into search parameters. Extract: PO number, client name, date range, keywords."
- Functions available to GPT: `search_po(query)`, `get_po_details(po_id)`, `export_po_json(po_id)`
- Route: `POST /api/chat` → accepts `{message, conversation_id}` → returns `{response, structured_data}`

#### 6. Conversation Flow
- Store conversation history in SQLite (optional: `conversations` table)
- GPT decides whether to:
  - Search for POs
  - Parse a specific document
  - Export data as JSON
  - Clarify user's query
- Example: User says "Metso firebrick order from Jan" → GPT extracts `{client: "Metso", keywords: ["firebrick"], date_range: "2024-01"}` → Backend searches → Returns results

### Phase 3: React Frontend

#### 7. Chat UI Components
- `ChatInterface.jsx`: Modern chat window with:
  - Message bubbles (user vs assistant)
  - Typing indicator during API calls
  - Display PO results as rich cards (not just text)
- `POResultCard.jsx`: Shows PO summary with:
  - PO number, date, client
  - Total value, item count
  - "View Details" button → expands full parsed data
  - "Export JSON" button → downloads structured data

#### 8. Search Bar Component
- `SearchBar.jsx`: Dual-mode interface:
  - Quick search input (direct query, no chat)
  - Button to switch to chat mode
- Debounced input for live suggestions (autocomplete from cached POs)

#### 9. API Integration
- `api.js`: Axios client with endpoints:
  - `sendChatMessage(message)` → POST `/api/chat`
  - `searchPOs(query)` → POST `/api/search`
  - `getPODetails(id)` → GET `/api/po/{id}`
  - `exportPO(id, format)` → GET `/api/po/{id}/export`

### Phase 4: Polish & Features

#### 10. Sync Mechanism
- Create `/api/sync` endpoint: Manually trigger full Gmail/Drive scan
- Background worker (optional): Use `apscheduler` to auto-sync every 24 hours
- Sync logic: Fetch all POs from last 2 years, parse, update cache

#### 11. Analytics & Filters
- Add filters in frontend: Date range, client, value range
- Route: `GET /api/analytics` → returns monthly PO value, top clients, etc.

#### 12. Error Handling & Edge Cases
- Handle OCR failures gracefully (fallback to GPT-4 Vision if configured)
- Handle duplicate POs (same PO in Gmail + Drive)
- Rate limiting for Google APIs (exponential backoff)

## Key Dependencies

### Backend
```
fastapi
uvicorn
sqlalchemy
google-auth-oauthlib
google-api-python-client
openai
PyPDF2 / pdfplumber
pytesseract
pdf2image
python-docx
python-dateutil
fuzzywuzzy
python-multipart
```

### Frontend
```
react
axios
tailwindcss
react-markdown (for chat formatting)
lucide-react (icons)
```

## Environment Variables (.env)

```env
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
OPENAI_API_KEY=sk-...
DATABASE_URL=sqlite:///./po_cache.db
REDIRECT_URI=http://localhost:8000/auth/callback
```

## Quick Start Checklist

1. Clone/setup repo structure
2. Install backend dependencies
3. Download Google OAuth credentials JSON from GCP Console
4. Run `uvicorn app.main:app --reload` (backend on :8000)
5. Install frontend dependencies (`npm install`)
6. Run `npm run dev` (frontend on :5173)
7. First-time OAuth: Visit `/auth/login` to authenticate
8. Trigger initial sync: `POST /api/sync`
9. Start chatting!

## Future Extensions (Post-MVP)

- WhatsApp bot integration (call `/api/chat` endpoint)
- ERP system webhook: Auto-notify on new PO arrival
- Advanced analytics dashboard (charts via Recharts)
- Multi-user support with role-based access
- Cloud deployment (Docker + Cloud Run / AWS ECS)

## Implementation To-Dos

- [ ] Initialize FastAPI project, setup SQLAlchemy with PO metadata model, configure environment variables
- [ ] Implement Google OAuth 2.0 flow and create Gmail/Drive API service wrappers
- [ ] Build document parsing engine with PDF, Word, and OCR support using Tesseract
- [ ] Implement fuzzy search service with metadata caching and Gmail/Drive integration
- [ ] Create GPT-4 chat interface with function calling for query interpretation and PO operations
- [ ] Initialize React app with TailwindCSS and create chat UI components
- [ ] Build API client and integrate chat/search components with backend endpoints
- [ ] Add sync endpoint and optional background worker for automatic Gmail/Drive scanning
- [ ] Add error handling, filters, analytics endpoint, and export functionality


