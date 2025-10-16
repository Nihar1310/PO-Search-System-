# 🔍 PO Search & Parsing System

An intelligent Purchase Order search and parsing system powered by AI that searches Gmail & Google Drive, extracts structured data, and enables natural language queries.

## 🎯 What This System Does

### 1. Centralized PO Search
- Search across **Gmail attachments** and **Google Drive** simultaneously
- Find any PO with just a number, client name, or keyword (e.g., "PO-45983", "Metso", "firebrick order")
- Results ranked by relevance - no more endless searching

### 2. Smart Parsing & Data Extraction
- Automatically extracts key information from POs:
  - 📦 PO number & date
  - 🏢 Buyer/client name
  - 📍 Billing and shipping addresses
  - 📑 Item list with quantities, unit prices, and total value
  - 💸 Payment & delivery terms
- Supports PDFs (text & scanned), Word documents via OCR

### 3. AI-Powered Chat Interface
- Natural language queries: "Find Metso firebrick order from January"
- GPT-4 interprets intent and executes searches
- Conversational experience with structured results

### 4. Structured Data Export
- Export PO data as JSON for integration with:
  - ERP systems
  - Quotation automation
  - Analytics dashboards
  - Internal workflows

## 🏗️ Architecture

**Backend**: FastAPI + SQLite + Google APIs + Enhanced OCR (Tesseract + Image Preprocessing) + OpenAI GPT-4  
**Frontend**: React + TailwindCSS + Modern Chat UI  
**Flow**: User query → GPT-4 interprets → Backend searches Gmail/Drive → Parse PO → Return structured data

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- Google Cloud Project with Gmail & Drive APIs enabled
- OpenAI API key
- Tesseract OCR (optional, for enhanced OCR capabilities)

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with your credentials

# Run the server
uvicorn app.main:app --reload
```

Backend runs on `http://localhost:8000`

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend runs on `http://localhost:5173`

### First-Time Setup

1. **Google OAuth**: Visit `http://localhost:8000/auth/login` to authenticate
2. **Initial Sync**: Trigger sync to index existing POs: `POST http://localhost:8000/api/sync`
   - Optional JSON body overrides default queries:
     ```json
     {
       "gmail_query": "filename:(po OR \"purchase order\")",
       "drive_query": "fullText contains 'purchase order'",
       "gmail_limit": 30,
       "drive_limit": 30
     }
     ```
   - Response example:
     ```json
     {
       "status": "completed",
       "summary": {
         "sources": {
           "gmail": {"fetched": 12, "query": "filename:(\"po\" OR \"purchase order\")", "error": null},
           "drive": {"fetched": 8, "query": "fullText contains \"purchase order\" or fullText contains \"PO\"", "error": null}
         },
         "ingested": 6,
         "duplicates": 14,
         "errors": []
       }
     }
     ```
3. **Start Chatting**: Open the frontend and start searching!

## 📁 Project Structure

```
po-project/
├── backend/               # FastAPI backend
│   ├── app/
│   │   ├── main.py       # Entry point
│   │   ├── routers/      # API routes (search, chat)
│   │   ├── services/     # Gmail, Drive, Parser, GPT services
│   │   └── utils/        # Auth & extractors
│   └── requirements.txt
├── frontend/             # React frontend
│   ├── src/
│   │   ├── components/   # Chat UI, Search, Results
│   │   └── services/     # API client
│   └── package.json
└── README.md
```

## 🔑 Environment Variables

Create a `.env` file in the `backend/` directory:

```env
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
DATABASE_URL=sqlite:///./po_cache.db
REDIRECT_URI=http://localhost:8000/auth/callback
GOOGLE_TOKEN_PATH=token.json
GOOGLE_SCOPES=https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/drive.readonly
GOOGLE_CLIENT_SECRETS_FILE=client_secret.json
USE_DOCAI=false
```

## 📖 API Endpoints

### Search & Chat
- `POST /api/chat` - Send chat message, get AI response
- `POST /api/search` - Direct PO search
- `GET /api/po/{id}` - Get PO details
- `GET /api/po/{id}/export` - Export PO as JSON

### System
- `GET /auth/login` - Generate Google OAuth consent URL
- `GET /auth/callback` - Exchange authorization code for tokens
- `GET /auth/status` - Check if Google credentials are stored
- `DELETE /auth/token` - Clear stored Google credentials
- `POST /api/sync` - Sync Gmail/Drive for new POs (returns summary of fetched/ingested documents)
- `GET /api/analytics` - Get PO analytics
- `GET /health` - Backend health check

## ⚡ Key Features

✅ **Fuzzy Search**: Find POs even with incomplete information  
✅ **Multi-Format Support**: PDF, Word, scanned documents  
✅ **Enhanced OCR**: Tesseract with image preprocessing for better accuracy  
✅ **Intelligent Caching**: Fast metadata search with on-demand document fetching  
✅ **Natural Language**: Chat with the system like a colleague  
✅ **Export Ready**: Structured JSON output for integrations  
✅ **Validation**: Input validation, text quality checks, and PO signal detection  

## 🔮 Future Extensions

- WhatsApp bot integration
- ERP system webhooks
- Advanced analytics dashboard
- Multi-user support with role-based access
- Cloud deployment (Docker + Cloud Run)

## 📝 License

MIT

## 🤝 Contributing

See `PLAN.md` for detailed implementation steps and architecture decisions.
