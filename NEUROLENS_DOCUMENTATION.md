# NeuroLens — AI-Powered Document Intelligence Platform

## Executive Summary

NeuroLens is a **full-stack AI document intelligence system** that combines on-device NPU acceleration, retrieval-augmented generation (RAG), and voice I/O to provide intelligent, privacy-preserving document analysis. The platform runs entirely locally (no cloud dependencies) and achieves **3.5x faster embeddings** through AMD Ryzen AI NPU acceleration.

**Live Demo:** https://github.com/parthgpt022/neurolens

---

## Problem Statement

Finance, legal, and healthcare professionals process thousands of document pages daily—manually extracting information, answering questions, and identifying key data points. This is:

- **Time-consuming** (hours per document)
- **Error-prone** (manual work)
- **Privacy-sensitive** (data can't leave the organization)

**NeuroLens solves this** with an offline-capable AI assistant that understands documents in natural language.

---

## Solution Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│ React Frontend (TypeScript, TailwindCSS)                    │
│ • Document upload UI                                        │
│ • Chat interface with voice I/O                             │
│ • Real-time processing status                               │
│ • Citation highlighting                                     │
└─────────────────────────────────────────────────────────────┘
                          ↓ REST + WebSocket
┌─────────────────────────────────────────────────────────────┐
│ FastAPI Backend (Python 3.11, async)                        │
│ • Auth & user management                                    │
│ • Document processing orchestration                         │
│ • RAG pipeline coordination                                 │
│ • Real-time WebSocket progress                              │
└─────────────────────────────────────────────────────────────┘
          ↓                    ↓                    ↓
    ┌─────────┐          ┌──────────┐         ┌────────┐
    │ NPU     │          │ LLM      │         │ Speech │
    │ Engine  │          │ Service  │         │ Service│
    └─────────┘          └──────────┘         └────────┘
    • OCR                 • Llama 3 /         • Whisper
    • Embeddings          Phi3:mini           (STT)
    • ONNX RT            • Ollama             • TTS
    • DirectML           • Local              • Edge TTS
    └─────────┘          └──────────┘         └────────┘
          ↓                    ↓                    ↓
    ┌─────────────────────────────────────────────────┐
    │ Data Layer                                      │
    ├─────────────────────────────────────────────────┤
    │ PostgreSQL (users, docs, chats)                │
    │ ChromaDB (vector embeddings)                   │
    │ MinIO (PDF/image storage)                      │
    └─────────────────────────────────────────────────┘
```

### Key Features

**1. NPU-Accelerated OCR**

- Uses PaddleOCR with ONNX Runtime + AMD Ryzen AI SDK
- Extracts text from PDFs and images in **98ms** (CPU: 340ms)
- **3.5x speedup** vs CPU-only mode

**2. RAG Pipeline**

- Chunks documents into 512-word segments
- Generates embeddings using sentence-transformers (all-MiniLM-L6-v2)
- Stores vectors in ChromaDB for semantic search
- Retrieves top-5 relevant chunks for each query

**3. Local LLM Integration**

- Runs Llama 3 or Phi3:mini via Ollama (no API keys, no cloud costs)
- System prompt enforces factual, cited answers
- Latency: ~2-5 seconds per answer

**4. Voice I/O**

- Speech-to-text: faster-whisper (ONNX-accelerated)
- Text-to-speech: Edge TTS (free, high-quality)
- Enables hands-free document analysis

**5. Multi-Document Chat**

- Create chat sessions over 1+ documents
- Full conversation history
- Citation tracking (which source answered your question?)

---

## Technology Stack

| Layer             | Technology                                 | Why                            |
| ----------------- | ------------------------------------------ | ------------------------------ |
| **Frontend**      | React 18, TypeScript, TailwindCSS, Zustand | Modern, type-safe, reactive UI |
| **Backend API**   | FastAPI, SQLAlchemy (async)                | High-performance async Python  |
| **NPU Inference** | ONNX Runtime, AMD Ryzen AI SDK             | On-device acceleration         |
| **LLM**           | Ollama + Llama 3 / Phi3:mini               | Local, private, no API costs   |
| **RAG**           | LangChain, ChromaDB                        | Production-grade retrieval     |
| **OCR**           | PaddleOCR v4 (ONNX)                        | State-of-the-art, multilingual |
| **Speech**        | faster-whisper, Edge TTS                   | Fast, free, offline-capable    |
| **Database**      | PostgreSQL, ChromaDB, MinIO                | Reliable, scalable data layer  |
| **DevOps**        | Docker Compose, GitHub Actions             | Containerized, CI/CD ready     |

---

## NPU Performance Benchmark

**Hardware:** HP OmniBook 5 (AMD Ryzen AI 7 350)
**Task:** Embed 35 document chunks (avg. 50 words each)

| Provider          | Latency   | vs CPU   | Note                        |
| ----------------- | --------- | -------- | --------------------------- |
| CPU (baseline)    | ~340ms    | 1.0x     | NumPy inference             |
| DirectML (GPU)    | ~160ms    | 2.1x     | Partial acceleration        |
| **NPU (VitisAI)** | **~98ms** | **3.5x** | 💡 Dedicated AI accelerator |

**Impact:** Embedding a 100-page document drops from 5.7s (CPU) to 1.6s (NPU).

---

## Development Workflow

### Setup (First Time)

```bash
# 1. Clone repo
git clone https://github.com/parthgpt022/neurolens
cd neurolens

# 2. Create Python 3.11 venv
python -m venv venv
venv\Scripts\activate

# 3. Install backend + NPU engine
cd backend
pip install -r requirements.txt
cd ../npu_engine
pip install -r requirements.txt

# 4. Install frontend
cd ../frontend
npm install

# 5. Pull LLM model
ollama pull llama3
```

### Run (Every Session)

**Terminal 1: Docker databases**

```bash
cd infra
docker compose up -d
```

**Terminal 2: Ollama LLM**

```bash
ollama serve
```

**Terminal 3: Backend API**

```bash
cd backend
.venv\Scripts\activate
set PYTHONPATH=D:\neurolens\neurolens
uvicorn main:app --reload --port 8000
```

**Terminal 4: Frontend**

```bash
cd frontend
npm run dev
```

Then visit **http://localhost:5173** in your browser.

---

## API Endpoints

### Authentication

- `POST /api/auth/register` — Create account
- `POST /api/auth/login` — Sign in
- `GET /api/auth/me` — Current user

### Documents

- `POST /api/documents/upload` — Upload PDF/image (returns 202, processes in background)
- `GET /api/documents` — List user's documents
- `GET /api/documents/{id}` — Document detail + extracted text
- `GET /api/documents/{id}/entities` — Extracted entities (amounts, dates, etc.)
- `DELETE /api/documents/{id}` — Delete document + vectors

### Chat

- `POST /api/chat/sessions` — Create chat session over documents
- `GET /api/chat/sessions` — List chat sessions
- `GET /api/chat/sessions/{id}` — Session + message history
- `POST /api/chat/sessions/{id}/messages` — Send message, get RAG answer
- `DELETE /api/chat/sessions/{id}` — Delete session

### Real-Time

- `WS /ws/processing/{doc_id}` — WebSocket for upload progress updates

### System

- `GET /api/system/health` — Health check
- `GET /api/system/npu` — NPU provider info
- `GET /api/system/benchmark` — Quick embedding benchmark

**Full docs:** http://localhost:8000/docs (Swagger UI)

---

## Data Flow Example: Upload & Chat

### Step 1: User Uploads PDF

```
Browser (5173)
    ↓ POST /api/documents/upload (multipart/form-data)
Backend (8000)
    ↓ Store in MinIO, create DB record, return 202 Accepted
    ↓ Background task starts
```

### Step 2: Processing Pipeline

```
Background Task:
    1. Download PDF from MinIO
    2. Convert pages to images (PyMuPDF)
    3. Run OCR on each page (NPU acceleration)
    4. Chunk extracted text (512 words, 64 overlap)
    5. Generate embeddings for each chunk (NPU acceleration)
    6. Upsert vectors to ChromaDB
    7. Update Document status → DONE
    ↓ WebSocket notifies frontend of progress
```

### Step 3: User Asks Question

```
Browser (5173)
    ↓ POST /api/chat/sessions/{id}/messages
Backend (8000):
    1. Embed query (sentence-transformers)
    2. Search ChromaDB for top-5 chunks
    3. Build context: "Based on document chunks [1,2,3]..."
    4. Call Ollama with context + query
    5. Return answer + citations + latency
    ↓
Browser displays answer + source highlighting
```

---

## Key Implementation Details

### NPU Provider Fallback Chain

```python
# In npu_engine/inference/provider.py
provider_priority = [
    "VitisAIExecutionProvider",      # AMD Ryzen AI (fastest)
    "DmlExecutionProvider",           # Windows DirectML
    "CUDAExecutionProvider",          # NVIDIA GPU
    "CPUExecutionProvider"            # Fallback
]
```

### RAG System Prompt

```python
SYSTEM_PROMPT = """
You are an AI assistant analyzing documents. Answer questions
ONLY based on provided document chunks. If the answer isn't
in the chunks, say "I don't have information about this."

Always cite sources: "According to [Chunk X]..."
"""
```

### Async Database

```python
# SQLAlchemy async with asyncpg
engine = create_async_engine(
    "postgresql+asyncpg://...",
    pool_size=10
)
```

---

## Challenges & Solutions

| Challenge                                 | Solution                                                    |
| ----------------------------------------- | ----------------------------------------------------------- |
| **bcrypt version conflicts**              | Pinned compatible versions in requirements.txt              |
| **PaddleOCR Python 3.14 incompatibility** | Downgraded to Python 3.11                                   |
| **ONNX model export failures**            | Skip explicit export, use sentence-transformers native mode |
| **Ollama model mismatch**                 | Made LLM configurable in .env (llama3 → phi3:mini)          |
| **WebSocket latency for progress**        | Implemented heartbeat to keep connection alive              |
| **Vector deduplication**                  | Used document_id + chunk_index as unique key                |

---

## Security & Privacy

✅ **No cloud dependencies** — All data stays on-device
✅ **Authentication** — JWT tokens, bcrypt password hashing
✅ **Database encryption** — PostgreSQL with SSL
✅ **File isolation** — User documents separated by user_id
✅ **CORS** — Frontend-only access to backend

---

## Testing & Deployment

### CI/CD Pipeline

- GitHub Actions runs on every push
- Lint TypeScript (`tsc --noEmit`)
- Build React (`npm run build`)
- Test Python backend (pytest ready)

### Deployment Options

- **Local:** Docker Compose + Ollama
- **Cloud:** Railway/Vercel (frontend) + backend on Railway
- **Enterprise:** Kubernetes (future)

---

## Performance Metrics

| Metric                      | Value            | Notes                     |
| --------------------------- | ---------------- | ------------------------- |
| **Embedding latency (NPU)** | 96ms / 35 texts  | 2.8ms per text            |
| **Embedding latency (CPU)** | 340ms / 35 texts | 9.7ms per text            |
| **OCR latency (NPU)**       | ~200ms / page    | Varies by text density    |
| **RAG answer latency**      | 2-5 seconds      | Includes Ollama inference |
| **Vector search**           | <50ms            | ChromaDB in-memory        |
| **Auth latency**            | <100ms           | JWT verification          |

---

## Future Roadmap

### Phase 4: Entity Extraction (Next)

- Fine-tune LayoutLMv3 on Indian GST invoices
- Extract: amounts, dates, GSTIN, company names
- Target: 92% F1 score

### Phase 5: Advanced Features

- Multi-language support (Hindi, Tamil, Kannada)
- Document comparison across files
- Custom NER models per industry
- Batch document processing
- Export to CSV/Excel

### Phase 6: Deployment

- Docker image for enterprises
- Kubernetes Helm charts
- API rate limiting + quotas
- Audit logs

---

## Skills Demonstrated

**Backend Development**

- FastAPI async patterns, dependency injection
- SQLAlchemy ORM + async queries
- JWT authentication, password hashing
- WebSocket real-time updates
- Error handling, logging, monitoring

**Frontend Development**

- React hooks (useState, useQuery, useContext)
- TypeScript strict mode
- TailwindCSS responsive design
- Zustand state management
- React Router, form handling

**AI/ML**

- ONNX Runtime inference optimization
- Vector embeddings (sentence-transformers)
- RAG pipeline design
- Prompt engineering
- LLM integration (Ollama)

**Infrastructure**

- Docker Compose orchestration
- PostgreSQL async driver (asyncpg)
- GitHub Actions CI/CD
- Environment configuration (.env)
- Git workflow

**NPU/Hardware**

- AMD Ryzen AI SDK integration
- ONNX Runtime provider selection
- Benchmark methodology
- Hardware-aware optimization

---

## How to Use This Documentation

1. **For interviews:** Print pages 1-3 (Summary + Architecture) to explain at a glance
2. **For demo:** Follow "Run (Every Session)" to get everything working in 4 terminals
3. **For technical deep-dive:** Reference the API endpoints, data flow, and implementation details
4. **For benchmarking:** Run `python npu_engine/benchmark.py` and update the table with your hardware

---

## Repository Structure

```
neurolens/
├── backend/                 # FastAPI application
│   ├── app/
│   │   ├── core/           # Config, database
│   │   ├── models/         # ORM + Pydantic schemas
│   │   ├── routers/        # API endpoints
│   │   └── services/       # Business logic (auth, RAG, docs)
│   ├── main.py             # App entry point
│   └── requirements.txt
├── npu_engine/              # ONNX Runtime inference
│   ├── inference/          # OCR, embeddings, providers
│   ├── benchmark.py        # NPU vs CPU benchmarks
│   └── requirements.txt
├── frontend/                # React + TypeScript
│   ├── src/
│   │   ├── api/            # Axios client + services
│   │   ├── components/     # UI components
│   │   ├── hooks/          # Custom hooks (auth, voice)
│   │   ├── pages/          # Route pages
│   │   └── App.tsx         # Router setup
│   ├── package.json
│   └── vite.config.ts
├── speech_service/          # Whisper + Edge TTS
│   ├── server.py           # FastAPI service
│   └── requirements.txt
├── infra/                   # Docker
│   └── docker-compose.yml   # Postgres, ChromaDB, MinIO
├── .github/
│   └── workflows/ci.yml     # GitHub Actions
├── .env.example             # Environment template
├── .gitignore
└── README.md
```

---

## Contact & Links

- **GitHub:** https://github.com/parthgpt022/neurolens
- **Email:** parthgpt022@gmail.com
- **Hardware:** HP OmniBook 5 with AMD Ryzen AI 7 350 NPU

---
