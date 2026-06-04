"""
npu_engine/inference/provider.py

Manages ONNX Runtime execution provider selection.
Tries NPU providers in order and falls back gracefully.
This lets you develop on CPU and deploy on NPU without changing any other code.
"""

import os
from typing import Optional
import onnxruntime as ort
from loguru import logger


# Priority order: best NPU first, CPU as final fallback
PROVIDER_PRIORITY = [
    "VitisAIExecutionProvider",   # AMD Ryzen AI NPU (best performance)
    "DmlExecutionProvider",        # DirectML — GPU/NPU on Windows (easier setup)
    "CUDAExecutionProvider",       # Nvidia GPU (if present)
    "CPUExecutionProvider",        # Always available
]


def get_available_providers() -> list[str]:
    """Return ONNX Runtime providers actually available on this machine."""
    return ort.get_available_providers()


def get_best_provider(preferred: Optional[str] = None) -> str:
    """
    Return the best available execution provider.
    
    Args:
        preferred: Force a specific provider (from .env NPU_EXECUTION_PROVIDER).
                   If it's not available, falls back through the priority list.
    """
    available = get_available_providers()
    logger.info(f"Available ONNX providers: {available}")

    # If caller requests a specific provider and it's available, use it
    if preferred and preferred in available:
        logger.info(f"Using requested provider: {preferred}")
        return preferred

    # Otherwise walk the priority list
    for provider in PROVIDER_PRIORITY:
        if provider in available:
            logger.info(f"Selected provider: {provider}")
            return provider

    # Should never reach here — CPUExecutionProvider is always available
    return "CPUExecutionProvider"


def build_session(
    model_path: str,
    preferred_provider: Optional[str] = None,
) -> tuple[ort.InferenceSession, str]:
    """
    Create an ONNX InferenceSession on the best available provider.

    Returns:
        (session, provider_name) — the session and which provider was used.
        Caller can log/display provider_name for the benchmark display.
    """
    if preferred_provider is None:
        preferred_provider = os.getenv(
            "NPU_EXECUTION_PROVIDER", "VitisAIExecutionProvider"
        )

    provider = get_best_provider(preferred_provider)

    # VitisAI needs a config dict pointing at the AMD compiler cache
    provider_options = []
    if provider == "VitisAIExecutionProvider":
        cache_dir = os.path.join(os.path.dirname(model_path), "vitisai_cache")
        os.makedirs(cache_dir, exist_ok=True)
        provider_options = [{
            "config_file": "",           # Use default config
            "cacheDir": cache_dir,
            "cacheKey": os.path.basename(model_path),
        }]

    session_options = ort.SessionOptions()
    session_options.graph_optimization_level = (
        ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    )
    # Reduce log noise from ONNX Runtime itself
    session_options.log_severity_level = 3

    try:
        if provider_options:
            session = ort.InferenceSession(
                model_path,
                sess_options=session_options,
                providers=[provider],
                provider_options=provider_options,
            )
        else:
            session = ort.InferenceSession(
                model_path,
                sess_options=session_options,
                providers=[provider, "CPUExecutionProvider"],
            )
        logger.success(f"Session created on [{provider}] for {model_path}")
        return session, provider

    except Exception as e:
        logger.warning(
            f"Failed to create session on {provider}: {e}. Falling back to CPU."
        )
        session = ort.InferenceSession(
            model_path,
            sess_options=session_options,
            providers=["CPUExecutionProvider"],
        )
        return session, "CPUExecutionProvider"
