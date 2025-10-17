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

**Backend**: FastAPI + SQLite + Google APIs + Google Document AI + Enhanced OCR (Tesseract + Image Preprocessing) + OpenAI GPT-4
**Frontend**: React + TailwindCSS + Modern Chat UI
**Flow**: User query → GPT-4 interprets → Backend searches Gmail/Drive → Parse PO (Document AI/OCR) → Return structured data

### Document AI Integration

The system now supports **Google Document AI** for superior text extraction and entity recognition:
- **Automatic Routing**: PDFs and images route through Document AI first when enabled
- **Entity Recognition**: Extracts structured entities (dates, addresses, line items) with confidence scores
- **Graceful Fallback**: Falls back to native PDF parsing or Tesseract OCR if Document AI unavailable
- **Metadata Preservation**: Document AI entity hints preserved in parse results for enhanced accuracy

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- Google Cloud Project with:
  - Gmail & Drive APIs enabled
  - Document AI API enabled (optional, for advanced parsing)
- OpenAI API key with billing configured
- Tesseract OCR (optional, for fallback OCR capabilities)

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
# Google OAuth Credentials
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_CLIENT_SECRETS_FILE=client_secret.json
GOOGLE_TOKEN_PATH=token.json
GOOGLE_SCOPES=https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/drive.readonly

# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Database
DATABASE_URL=sqlite:///./po_cache.db

# OAuth
REDIRECT_URI=http://localhost:8000/auth/callback

# Document AI (Optional - for advanced parsing)
USE_DOCAI=false
DOCAI_PROJECT_ID=your-gcp-project-id
DOCAI_LOCATION=us
DOCAI_PROCESSOR_ID=your-processor-id
DOCAI_PROCESSOR_VERSION=  # Optional: specific version
DOCAI_API_ENDPOINT=  # Optional: e.g., us-documentai.googleapis.com
```

### 🤖 Document AI Setup (Optional but Recommended)

Document AI provides superior text extraction with entity recognition. To enable:

1. **Enable Document AI API** in Google Cloud Console:
   ```bash
   gcloud services enable documentai.googleapis.com
   ```

2. **Create a Document Processor**:
   - Go to [Document AI Console](https://console.cloud.google.com/ai/document-ai/processors)
   - Create a new processor (choose "Form Parser" or "OCR Processor")
   - Note the **Processor ID** and **Location** (e.g., "us", "eu")

3. **Set up Service Account**:
   ```bash
   # Create service account
   gcloud iam service-accounts create docai-po-parser \
     --display-name="Document AI PO Parser"
   
   # Grant Document AI User role
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:docai-po-parser@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/documentai.apiUser"
   
   # Create and download key
   gcloud iam service-accounts keys create docai-key.json \
     --iam-account=docai-po-parser@YOUR_PROJECT_ID.iam.gserviceaccount.com
   ```

4. **Configure Environment**:
   ```bash
   # Set credentials path
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/docai-key.json"
   
   # Update .env
   USE_DOCAI=true
   DOCAI_PROJECT_ID=your-gcp-project-id
   DOCAI_LOCATION=us
   DOCAI_PROCESSOR_ID=your-processor-id-from-console
   ```

5. **Install Dependencies**:
   ```bash
   pip install google-cloud-documentai
   ```

6. **Restart Backend**:
   ```bash
   uvicorn app.main:app --reload
   ```

**How It Works:**
- When `USE_DOCAI=true`, PDFs and images route through Document AI first
- Document AI extracts text with entity hints (dates, amounts, addresses)
- If Document AI fails or is unavailable, system falls back to native/OCR parsing
- Entity metadata preserved in `parsed_data.docai` field for enhanced accuracy

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
✅ **Document AI Integration**: Google Document AI for superior text extraction and entity recognition
✅ **Enhanced OCR**: Tesseract with image preprocessing for better accuracy
✅ **Intelligent Caching**: Fast metadata search with on-demand document fetching
✅ **Natural Language**: Chat with the system like a colleague
✅ **Export Ready**: Structured JSON output for integrations
✅ **Validation**: Input validation, text quality checks, and PO signal detection
✅ **Graceful Fallback**: Multi-layer parsing strategy (Document AI → Native → OCR)

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
