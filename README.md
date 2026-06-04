# 🧠 NeuroLens — AI-Powered Document Intelligence Platform

> On-device NPU-accelerated document analysis with RAG, voice Q&A, and financial entity extraction.

[![CI](https://github.com/YOUR_USERNAME/neurolens/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/neurolens/actions)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![React](https://img.shields.io/badge/React-18-61DAFB)
![License](https://img.shields.io/badge/license-MIT-green)

<!-- Add a demo GIF here after Week 3: ![Demo](docs/demo.gif) -->

## What it does

NeuroLens turns any PDF or scanned document into a queryable knowledge base — entirely on your local machine, with no data sent to external servers for processing.

- **Upload** a PDF, invoice, contract, or financial report
- **NPU-accelerated OCR** extracts text from every page in milliseconds
- **Ask questions** in natural language or by voice → grounded answers with citations
- **Entity extraction** pulls out amounts, dates, GSTIN, company names automatically
- **Multi-document comparison** across multiple files in one chat session

**Demo target**: Upload a GST invoice → ask "what is the total tax?" by voice → hear the spoken answer in < 3 seconds.

---

## NPU Benchmark

> Measured on HP OmniBook 5 (AMD Ryzen AI 7 350) vs CPU-only mode.
> Run `python npu_engine/benchmark.py` to reproduce.

| Task | CPU (ms) | NPU/DirectML (ms) | Speedup |
|---|---|---|---|
| Embedding batch (35 texts) | — | — | — |
| Embedding single text | — | — | — |
| OCR (A4 page) | — | — | — |

*Fill in after running benchmark.py on your machine — these numbers are your strongest talking point.*

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  React 18 + TypeScript + TailwindCSS (Vite)                 │
│  Upload · Chat UI · Voice I/O · Entity Dashboard            │
└────────────────────┬────────────────────────────────────────┘
                     │ REST + WebSocket
┌────────────────────▼────────────────────────────────────────┐
│  FastAPI Backend  (Python 3.11, async)                      │
│  Auth · Document Management · Chat Sessions · RAG           │
└──────┬──────────────────────┬──────────────────────────────-┘
       │                      │
┌──────▼──────┐     ┌─────────▼──────────┐     ┌────────────┐
│ NPU Engine  │     │  LLM / RAG Service │     │  Speech    │
│ ONNX Runtime│     │  LangChain + Ollama│     │  Whisper   │
│ VitisAI EP  │     │  (Llama 3 local)   │     │  Edge TTS  │
└──────┬──────┘     └─────────┬──────────┘     └────────────┘
       │                      │
┌──────▼──────┐     ┌─────────▼──────────┐     ┌────────────┐
│ PostgreSQL  │     │  ChromaDB          │     │  MinIO     │
│ (metadata)  │     │  (vector search)   │     │  (files)   │
└─────────────┘     └────────────────────┘     └────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, TailwindCSS, Zustand, React Query |
| Backend | FastAPI, SQLAlchemy (async), PostgreSQL, Alembic |
| NPU Inference | ONNX Runtime, AMD Ryzen AI SDK (VitisAI EP) |
| LLM | Llama 3 8B via Ollama (local, free, private) |
| RAG | LangChain, ChromaDB (vector search), MiniLM-L6 embeddings |
| OCR | PaddleOCR v4 (ONNX) |
| Speech | faster-whisper (STT), Edge TTS (TTS) |
| Storage | MinIO (S3-compatible, local) |
| DevOps | Docker Compose, GitHub Actions CI/CD |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker Desktop (for Postgres, MinIO, ChromaDB)
- [Ollama](https://ollama.ai/download) installed and running
- AMD Ryzen AI SDK (optional — falls back to CPU automatically)

### 1. Clone and configure

```bash
git clone https://github.com/YOUR_USERNAME/neurolens
cd neurolens
cp .env.example .env   # Edit if needed — defaults work for local dev
```

### 2. Start infrastructure

```bash
cd infra
docker compose up -d
# Postgres: localhost:5432
# MinIO:    localhost:9000 (console: 9001)
# ChromaDB: localhost:8001
```

### 3. Start Ollama + pull model

```bash
# Install from https://ollama.ai/download, then:
ollama pull llama3
ollama serve   # Keep this running
```

### 4. Start backend

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

### 5. Start NPU engine (separate terminal)

```bash
cd npu_engine
pip install -r requirements.txt
# Export embedding model to ONNX (first time only, ~30s):
python -c "from inference.embedding_runner import export_to_onnx; export_to_onnx()"
# Run benchmark to confirm NPU is working:
python benchmark.py
```

### 6. Start speech service (optional)

```bash
cd speech_service
pip install -r requirements.txt
uvicorn server:app --port 8002 --reload
```

### 7. Start frontend

```bash
cd frontend
npm install
npm run dev
# Open: http://localhost:5173
```

---

## Project Structure

```
neurolens/
├── backend/          # FastAPI API + business logic
├── npu_engine/       # ONNX inference with NPU provider
├── llm_service/      # RAG chains (future: separate service)
├── speech_service/   # Whisper STT + Edge TTS
├── frontend/         # React + TypeScript UI
├── ml_training/      # Fine-tuning scripts (Phase 4)
├── infra/            # Docker Compose + Kubernetes
└── .github/          # CI/CD workflows
```

---

## Development Roadmap

- [x] Phase 1: NPU OCR pipeline + FastAPI skeleton
- [x] Phase 2: RAG with ChromaDB + Llama 3
- [x] Phase 3: React frontend + voice I/O
- [ ] Phase 4: NER fine-tuning for Indian financial documents
- [ ] Phase 5: Docker polish + deployment + demo video

---

## Built With

This project was built as a portfolio project combining CS + FinTech coursework.
Hardware: HP OmniBook 5 with AMD Ryzen AI 7 350 (dedicated NPU, 16 TOPS).

---

## License

MIT
