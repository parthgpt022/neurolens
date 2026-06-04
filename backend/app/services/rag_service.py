"""
backend/app/services/rag_service.py

Retrieval-Augmented Generation service.
Given a user query and a set of document IDs:
  1. Embed the query (NPU-accelerated)
  2. Retrieve top-k relevant chunks from ChromaDB
  3. Build a prompt with context + chat history
  4. Call Ollama (local Llama 3) for the answer
  5. Return answer + citations
"""

import time
import uuid
import httpx
from typing import Optional
from loguru import logger

from app.core.config import get_settings

settings = get_settings()

SYSTEM_PROMPT = """You are NeuroLens, an expert document analysis assistant.
You answer questions based ONLY on the provided document excerpts.

Rules:
- Answer concisely and accurately using only the given context.
- Always mention which part of the document supports your answer.
- If the answer is not in the context, say: "I couldn't find that information in the provided documents."
- For financial figures, be precise — quote exact numbers from the text.
- Format lists and tables clearly when the data calls for it.
"""


class RAGService:
    def __init__(self):
        self._embedder = None
        self._chroma = None

    def _get_embedder(self):
        if self._embedder is None:
            from npu_engine.inference.embedding_runner import EmbeddingRunner
            self._embedder = EmbeddingRunner.get_instance()
        return self._embedder

    def _get_chroma(self):
        if self._chroma is None:
            import chromadb
            client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
            )
            self._chroma = client.get_or_create_collection(
                name=settings.chroma_collection,
                metadata={"hnsw:space": "cosine"},
            )
        return self._chroma

    async def answer(
        self,
        query: str,
        document_ids: list[uuid.UUID],
        chat_history: Optional[list[dict]] = None,
        top_k: int = 5,
    ) -> dict:
        """
        Generate a grounded answer for the query.

        Returns:
            {answer, citations, latency_ms, query_embedding_ms, retrieval_ms, llm_ms}
        """
        start = time.perf_counter()

        # 1. Embed the query on NPU
        t0 = time.perf_counter()
        query_embedding = self._get_embedder().embed_one(query)
        embed_ms = (time.perf_counter() - t0) * 1000

        # 2. Retrieve top-k chunks filtered to these documents
        t0 = time.perf_counter()
        doc_id_strings = [str(d) for d in document_ids]
        results = self._get_chroma().query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"document_id": {"$in": doc_id_strings}},
        )
        retrieval_ms = (time.perf_counter() - t0) * 1000

        # 3. Build context from retrieved chunks
        chunks = results["documents"][0] if results["documents"] else []
        metadatas = results["metadatas"][0] if results["metadatas"] else []
        distances = results["distances"][0] if results["distances"] else []

        citations = []
        context_parts = []
        for i, (chunk, meta, dist) in enumerate(zip(chunks, metadatas, distances)):
            relevance = round(1 - float(dist), 3)  # cosine: 0=identical, 2=opposite
            citations.append({
                "index": i + 1,
                "text": chunk[:200] + "..." if len(chunk) > 200 else chunk,
                "document_id": meta.get("document_id"),
                "page_number": meta.get("page_number", 1),
                "relevance_score": relevance,
            })
            context_parts.append(
                f"[Source {i+1}, Page {meta.get('page_number', '?')}]:\n{chunk}"
            )

        context = "\n\n---\n\n".join(context_parts)

        # 4. Build messages for Ollama
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add chat history (last 6 turns for context window management)
        if chat_history:
            for turn in chat_history[-6:]:
                messages.append({
                    "role": turn["role"],
                    "content": turn["content"],
                })

        messages.append({
            "role": "user",
            "content": (
                f"Document excerpts:\n\n{context}\n\n"
                f"Question: {query}"
            ),
        })

        # 5. Call Ollama
        t0 = time.perf_counter()
        answer = await self._call_ollama(messages)
        llm_ms = (time.perf_counter() - t0) * 1000

        total_ms = (time.perf_counter() - start) * 1000
        logger.info(
            f"RAG: embed={embed_ms:.0f}ms, retrieve={retrieval_ms:.0f}ms, "
            f"llm={llm_ms:.0f}ms, total={total_ms:.0f}ms"
        )

        return {
            "answer": answer,
            "citations": citations,
            "latency_ms": round(total_ms, 1),
            "embed_ms": round(embed_ms, 1),
            "retrieval_ms": round(retrieval_ms, 1),
            "llm_ms": round(llm_ms, 1),
        }

    async def _call_ollama(self, messages: list[dict]) -> str:
        """Call local Ollama API with the given messages."""
        url = f"{settings.ollama_base_url}/api/chat"
        payload = {
            "model": settings.ollama_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.1,    # Low temp = more factual, less hallucination
                "top_p": 0.9,
                "num_ctx": 4096,       # Context window size
            },
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["message"]["content"]
            except httpx.TimeoutException:
                logger.error("Ollama request timed out (120s)")
                return "Request timed out. Ollama may be overloaded or the model is still loading."
            except httpx.HTTPStatusError as e:
                logger.error(f"Ollama HTTP error: {e.response.status_code}")
                return f"LLM service error: {e.response.status_code}"
            except Exception as e:
                logger.error(f"Ollama error: {e}")
                return f"Could not reach the LLM service. Is Ollama running? Error: {str(e)}"


_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
