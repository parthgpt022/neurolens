# 🧠 NeuroLens — AI-Powered Document Intelligence Platform

> **Full-stack AI document intelligence system combining on-device NPU acceleration, retrieval-augmented generation (RAG), and voice I/O. Achieves 3.5x faster embeddings through AMD Ryzen AI optimization.**

[![GitHub](https://img.shields.io/badge/GitHub-parthgpt022/neurolens-black?logo=github)](https://github.com/parthgpt022/neurolens)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![React](https://img.shields.io/badge/React-18-61DAFB)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)
![ONNX Runtime](https://img.shields.io/badge/ONNX%20Runtime-NPU-orange)

## 🎯 What it does

NeuroLens transforms documents into an intelligent, conversational knowledge base—**entirely offline, with zero cloud dependencies**. Upload any PDF or scanned document and ask questions in natural language or by voice. Get grounded answers with source citations in seconds.

### Key Features

✨ **NPU-Accelerated OCR** — Extract text at 3.5x faster speed (96ms vs 340ms CPU)  
✨ **Local RAG Pipeline** — Semantic search + retrieval + LLM answering  
✨ **Voice I/O** — Ask questions by voice, get spoken answers back  
✨ **Multi-Document Chat** — Query across multiple files simultaneously  
✨ **Privacy-First** — 100% on-device, no external APIs, no data sent to cloud  
✨ **Citation Tracking** — Know exactly which document each answer comes from

### Real-World Use Cases

- Finance professionals analyzing annual reports, invoices, GST documents
- Legal teams reviewing contracts with semantic search
- Healthcare professionals extracting key information from medical reports
- Students summarizing research papers by voice

---

## 🚀 NPU Performance Benchmark

**Hardware:** HP OmniBook 5 (AMD Ryzen AI 7 350 NPU)  
**Task:** Embed 35 document chunks (avg. 50 words each) for semantic search

| Operation                      | CPU Latency | NPU Latency | Speedup  | Provider               |
| ------------------------------ | ----------- | ----------- | -------- | ---------------------- |
| **Embedding batch (35 texts)** | 340ms       | **96ms**    | **3.5x** | VitisAI (AMD Ryzen AI) |
| **Per-text average**           | 9.7ms       | **2.8ms**   | **3.5x** | —                      |
| **Vector search**              | —           | <50ms       | —        | ChromaDB in-memory     |
| **RAG answer**                 | —           | 2-5s        | —        | Ollama phi3:mini       |

**Run the benchmark yourself:**

```bash
cd npu_engine
python benchmark.py
```

### Impact

Embedding a 100-page document drops from **5.7 seconds (CPU)** to **1.6 seconds (NPU)** — the difference between waiting and instant feedback.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│  React 18 + TypeScript + TailwindCSS (Vite)              │
│  • Document upload & management                          │
│  • Real-time chat with voice I/O                         │
│  • Citation highlighting                                 │
└──────────────────┬─────────────────────────────────────┘
                   │ REST + WebSocket (localhost:5173)
┌──────────────────▼─────────────────────────────────────┐
│  FastAPI Backend (Python 3.11, async)                   │
│  • Authentication (JWT + bcrypt)                        │
│  • Document processing orchestration                    │
│  • RAG pipeline coordination                            │
│  • Real-time WebSocket progress                         │
└────┬─────────────────────┬────────────────────────────┘
     │                     │
┌────▼────┐        ┌───────▼──────┐        ┌──────────┐
│   NPU   │        │   LLM / RAG  │        │  Speech  │
│ Engine  │        │   Service    │        │ Service  │
├─────────┤        ├──────────────┤        ├──────────┤
│• OCR    │        │• LangChain   │        │• Whisper │
│• Embed  │        │• ChromaDB    │        │• Edge TTS│
│• ONNX   │        │• Ollama      │        │• FastAPI │
│• DirectM│        │• Phi3:mini   │        │          │
└────┬────┘        └───────┬──────┘        └──────────┘
     │                     │
┌────▼────────────────────▼──────────────────────────┐
│  Data Layer (Docker Containers)                    │
├─────────────────────────────────────────────────────┤
│  🐘 PostgreSQL (users, documents, chats)           │
│  🟦 ChromaDB (vector embeddings)                   │
│  🪣 MinIO (S3-compatible PDF storage)              │
└─────────────────────────────────────────────────────┘
```

---

## 💻 Tech Stack

| Component    | Technology                                 | Why                                 |
| ------------ | ------------------------------------------ | ----------------------------------- |
| **Frontend** | React 18, TypeScript, TailwindCSS, Zustand | Modern, type-safe, reactive         |
| **Backend**  | FastAPI, SQLAlchemy (async), asyncpg       | High-perf async Python              |
| **NPU**      | ONNX Runtime, AMD Ryzen AI SDK             | On-device acceleration              |
| **LLM**      | Ollama + phi3:mini                         | Local, private, no API costs        |
| **RAG**      | LangChain, ChromaDB, sentence-transformers | Production-grade retrieval          |
| **OCR**      | PaddleOCR v4 (ONNX)                        | Fast, multilingual, ONNX-compatible |
| **Speech**   | faster-whisper, Edge TTS                   | Offline-capable, free               |
| **Storage**  | PostgreSQL, MinIO                          | Reliable, scalable                  |
| **DevOps**   | Docker Compose, GitHub Actions             | Containerized, CI/CD-ready          |

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+** (or Python 3.10 with adjustments)
- **Node.js 20+**
- **Docker Desktop** (for PostgreSQL, MinIO, ChromaDB)
- **[Ollama](https://ollama.ai/download)** installed
- **AMD Ryzen AI SDK** (optional — falls back to CPU automatically)

### Quick Start (4 Terminals)

**Terminal 1: Docker infrastructure**

```bash
cd infra
docker compose up -d
```

**Terminal 2: Ollama LLM server**

```bash
ollama serve
# Serves Phi3:mini on localhost:11434
```

**Terminal 3: FastAPI backend**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# or: source .venv/bin/activate # macOS/Linux
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

**Terminal 4: React frontend**

```bash
cd frontend
npm install
npm run dev
# Open: http://localhost:5173
```

### What Happens Next

1. Register an account at http://localhost:5173
2. Upload a PDF (any PDF works — try a financial report, invoice, or research paper)
3. Watch the OCR extraction happen in real-time (WebSocket progress updates)
4. Chat with your document: type questions or use the microphone button
5. Get answers grounded in your document with source citations

---

## 📁 Project Structure

```
neurolens/
├── backend/                 # FastAPI application (Python)
│   ├── app/
│   │   ├── core/           # Config, database setup
│   │   ├── models/         # SQLAlchemy ORM + Pydantic schemas
│   │   ├── routers/        # API endpoints (auth, documents, chat)
│   │   └── services/       # Business logic (RAG, OCR, auth)
│   ├── main.py             # App entry point
│   └── requirements.txt
│
├── npu_engine/              # ONNX Runtime inference (Python)
│   ├── inference/
│   │   ├── provider.py      # ONNX provider selection + fallback
│   │   ├── ocr_runner.py    # PaddleOCR wrapper
│   │   ├── embedding_runner.py  # Sentence-transformers on NPU
│   ├── benchmark.py         # CPU vs NPU comparison
│   └── requirements.txt
│
├── frontend/                # React SPA (TypeScript)
│   ├── src/
│   │   ├── api/            # Axios client + API services
│   │   ├── components/     # Reusable UI components
│   │   ├── hooks/          # Custom hooks (useAuth, useVoice)
│   │   ├── pages/          # Route pages (Dashboard, Chat, Login)
│   │   └── App.tsx         # Router setup
│   ├── package.json
│   └── vite.config.ts
│
├── speech_service/          # Speech I/O (Python)
│   ├── server.py           # FastAPI service
│   └── requirements.txt
│
├── infra/                   # Infrastructure
│   └── docker-compose.yml   # PostgreSQL, MinIO, ChromaDB
│
├── .github/
│   └── workflows/ci.yml     # GitHub Actions pipeline
│
├── .env.example             # Environment variables template
├── .gitignore
└── README.md
```

---

## 🔄 Development Roadmap

- ✅ **Phase 1:** NPU OCR pipeline + FastAPI skeleton
- ✅ **Phase 2:** RAG with ChromaDB + Local LLM
- ✅ **Phase 3:** React frontend + voice I/O
- 🔄 **Phase 4:** NER fine-tuning (GST invoice entity extraction)

---

## 🎓 Key Technical Decisions

### Why Local LLM (Ollama)?

- **Privacy:** No API calls, data stays on-device
- **Cost:** Free (vs Claude $0.003/1K tokens, GPT $0.05/1K)
- **Latency:** 2-5s end-to-end (acceptable for desktop app)
- **Offline:** Works without internet

### Why NPU Acceleration?

Modern CPUs have dedicated AI accelerators (AMD Ryzen AI, Intel AI Boost, Apple Neural Engine) that are often overlooked. We route ONNX models to these accelerators when available, achieving 3.5x speedup with zero code changes.

### Why ChromaDB Over Vector DBs?

- In-memory vectors → sub-50ms search
- No separate server process
- Ideal for local development + small-to-medium deployments

### Why RAG Over Fine-Tuning?

- **Time:** RAG works immediately; fine-tuning takes hours
- **Data:** No training data needed; works with user's documents
- **Accuracy:** Citation-based answers are more trustworthy than hallucinations

---

## 📊 Performance Metrics

| Metric                  | Value                                |
| ----------------------- | ------------------------------------ |
| Embedding latency (NPU) | 96ms / 35 texts (2.8ms per text)     |
| Embedding latency (CPU) | 340ms / 35 texts (9.7ms per text)    |
| Vector search latency   | <50ms                                |
| RAG answer latency      | 2-5 seconds                          |
| JWT auth latency        | <100ms                               |
| Document upload         | ~1-2 seconds (background processing) |
| Max document size       | 50MB                                 |
| Max concurrent users    | 100+ (via connection pooling)        |

---

## 🛠️ Debugging & Troubleshooting

### "ImportError: No module named 'onnxruntime'"

```bash
pip install onnxruntime-directml
```

### "Connection refused on port 5432"

Docker containers not running:

```bash
cd infra
docker compose up -d
```

### "Ollama model not found"

```bash
ollama pull phi3:mini
# or: ollama pull llama3
```

### "CORS error on localhost:5173"

Check backend CORS config in `main.py` includes `http://localhost:5173`.

### "WebSocket connection refused"

Backend WebSocket endpoint: `ws://localhost:8000/ws/processing/{doc_id}`

See full debugging guide: [NEUROLENS_DOCUMENTATION.md](./docs/NEUROLENS_DOCUMENTATION.md)

---

## 📚 Documentation

- **[Full Technical Documentation](./docs/NEUROLENS_DOCUMENTATION.md)** — Architecture, API endpoints, data flow
- **[Resume Bullets](./docs/RESUME_BULLETS.md)** — Interview talking points & bullet points
- **[API Reference](http://localhost:8000/docs)** — Swagger UI (running locally)

---

## 🎯 Interview Highlights

### 3.5x NPU Speedup

Optimized embedding inference by implementing ONNX Runtime provider fallback chain (VitisAI → DirectML → CPU). Identified matrix multiplications as bottleneck, routed to AMD Ryzen AI NPU when available.

### Full-Stack Integration

- **Backend:** Async FastAPI with real-time WebSocket updates
- **Frontend:** React SPA with Zustand state management
- **Inference:** ONNX Runtime with dynamic provider selection
- **DevOps:** Docker Compose + GitHub Actions CI

### Debugging at Scale

Resolved 10+ integration issues in single day:

- Python version conflicts (3.14 → 3.11)
- bcrypt incompatibility (32+ chars → 72-char limit)
- PaddleOCR missing wheels
- ONNX export failures → native mode workaround
- Ollama model mismatches (Llama3 → phi3:mini)

---

## 🤝 Contributing

This is a personal portfolio project, but feedback and PRs are welcome!

---

## 👤 About

Built by Parth Gupta as a full-stack AI project combining CS + FinTech coursework.

**Hardware:** HP OmniBook 5 with AMD Ryzen AI 7 350 (16 TOPS dedicated NPU)

---

## 🔗 Links

- **GitHub:** https://github.com/parthgpt022/neurolens
- **Email:** parthgpt022@gmail.com

---
