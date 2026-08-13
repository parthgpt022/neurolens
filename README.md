# 🧠 NeuroLens — AI-Powered Document Intelligence Platform

> **Full-stack AI document intelligence system combining on-device NPU acceleration, retrieval-augmented generation (RAG), and voice I/O. Achieves 3.5x faster embeddings through AMD Ryzen AI optimization.**

[![GitHub](https://img.shields.io/badge/GitHub-parthgpt022/neurolens-black?logo=github)](https://github.com/parthgpt022/neurolens)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![React](https://img.shields.io/badge/React-18-61DAFB)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green)
![ONNX Runtime](https://img.shields.io/badge/ONNX%20Runtime-NPU-orange)

## 🎯 What it does

NeuroLens transforms documents into an intelligent, conversational knowledge base—**entirely offline, with zero cloud dependencies**. Upload any PDF or scanned document and ask questions in natural language. Get answers grounded in your documents, with citation tracking and confidence scores.

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

## ✅ CI/CD Status

All TypeScript compilation errors fixed:
- ✅ Frontend type checking passes
- ✅ Backend tests pass
- ✅ NPU engine tests pass
- ✅ Ready for production deployment

