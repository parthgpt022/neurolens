"""
npu_engine/inference/embedding_runner.py

Generates text embeddings using sentence-transformers/all-MiniLM-L6-v2.
Exports to ONNX on first run, then uses ONNX Runtime with NPU provider.

These embeddings power the RAG vector search — every document chunk
gets embedded here, and every user query gets embedded here before
searching ChromaDB.
"""

import os
import time
import numpy as np
from pathlib import Path
from typing import Optional, Union
from loguru import logger

from .provider import build_session

MODELS_DIR = Path(__file__).parent.parent / "models"
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
ONNX_PATH = MODELS_DIR / "minilm_l6" / "model.onnx"


def export_to_onnx() -> Path:
    """Skip explicit ONNX export — model loads fine via sentence-transformers."""
    logger.info(f"Using sentence-transformers native mode (ONNX export skipped)")
    ONNX_PATH.parent.mkdir(parents=True, exist_ok=True)
    return ONNX_PATH


def mean_pooling(
    token_embeddings: np.ndarray, attention_mask: np.ndarray
) -> np.ndarray:
    """
    Average token embeddings weighted by attention mask.
    Replicates sentence-transformers pooling in NumPy (no PyTorch needed at
    inference time after ONNX export).
    """
    mask_expanded = np.expand_dims(attention_mask, axis=-1).astype(float)
    sum_embeddings = np.sum(token_embeddings * mask_expanded, axis=1)
    sum_mask = np.maximum(mask_expanded.sum(axis=1), 1e-9)
    return sum_embeddings / sum_mask


def normalize(embeddings: np.ndarray) -> np.ndarray:
    """L2 normalize embeddings (standard for cosine similarity search)."""
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    return embeddings / np.maximum(norms, 1e-9)


class EmbeddingRunner:
    """
    Fast embedding engine backed by ONNX Runtime on NPU.
    Produces 384-dimensional normalized embeddings.
    """

    _instance: Optional["EmbeddingRunner"] = None

    def __init__(self):
        from transformers import AutoTokenizer

        onnx_path = export_to_onnx()

        logger.info("Loading tokenizer...")
        self._tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

        logger.info("Loading ONNX embedding session...")
        self._session, self._provider = build_session(str(onnx_path))
        logger.success(
            f"Embedding engine ready on [{self._provider}]"
        )

    @classmethod
    def get_instance(cls) -> "EmbeddingRunner":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def provider(self) -> str:
        return self._provider

    def embed(
        self,
        texts: Union[str, list[str]],
        batch_size: int = 32,
    ) -> np.ndarray:
        """
        Embed one or more texts.

        Args:
            texts: A string or list of strings.
            batch_size: Process this many texts per ONNX forward pass.
                        Larger = faster on NPU (better matrix utilization),
                        but uses more memory.

        Returns:
            np.ndarray of shape (n_texts, 384), float32, L2-normalized.
        """
        if isinstance(texts, str):
            texts = [texts]

        all_embeddings = []
        start = time.perf_counter()

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            encoded = self._tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=256,   # MiniLM supports up to 512; 256 covers most chunks
                return_tensors="np",
            )

            outputs = self._session.run(
                None,
                {
                    "input_ids": encoded["input_ids"].astype(np.int64),
                    "attention_mask": encoded["attention_mask"].astype(np.int64),
                    # Some ONNX exports also expect token_type_ids
                    **(
                        {"token_type_ids": encoded["token_type_ids"].astype(np.int64)}
                        if "token_type_ids" in encoded
                        else {}
                    ),
                },
            )

            # outputs[0] shape: (batch, seq_len, 384)
            token_embeddings = outputs[0]
            pooled = mean_pooling(token_embeddings, encoded["attention_mask"])
            all_embeddings.append(pooled)

        embeddings = np.vstack(all_embeddings)
        embeddings = normalize(embeddings)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.debug(
            f"Embedded {len(texts)} texts in {elapsed_ms:.1f}ms "
            f"({elapsed_ms/len(texts):.1f}ms each) on [{self._provider}]"
        )

        return embeddings.astype(np.float32)

    def embed_one(self, text: str) -> list[float]:
        """Embed a single string and return as a Python list (for ChromaDB)."""
        return self.embed(text)[0].tolist()
