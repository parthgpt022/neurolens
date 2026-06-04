"""
npu_engine/inference/ocr_runner.py

Runs OCR on document images using PaddleOCR.
The detection and recognition models are exported to ONNX and run
via the NPU execution provider for maximum speed.

Pipeline:
  image → text detection (find word bounding boxes) → 
  text recognition (read each box) → structured output
"""

import time
from pathlib import Path
from typing import Optional
import numpy as np
from PIL import Image
from loguru import logger

# PaddleOCR handles its own ONNX-based pipeline
# We configure it to use our ONNX models explicitly
from paddleocr import PaddleOCR


class OCRResult:
    """Structured result from OCR inference."""

    def __init__(self, raw_result: list, image_size: tuple[int, int]):
        self.lines: list[dict] = []
        self.full_text: str = ""
        self.image_size = image_size  # (width, height)

        all_text_parts = []
        if raw_result and raw_result[0]:
            for line in raw_result[0]:
                bbox, (text, confidence) = line
                self.lines.append({
                    "text": text,
                    "confidence": round(float(confidence), 4),
                    # bbox is [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
                    "bbox": bbox,
                    # Normalized bbox for frontend highlighting (0.0–1.0)
                    "bbox_norm": self._normalize_bbox(bbox, image_size),
                })
                if confidence > 0.5:
                    all_text_parts.append(text)

        self.full_text = "\n".join(all_text_parts)

    def _normalize_bbox(
        self, bbox: list, size: tuple[int, int]
    ) -> dict[str, float]:
        w, h = size
        xs = [pt[0] for pt in bbox]
        ys = [pt[1] for pt in bbox]
        return {
            "x": min(xs) / w,
            "y": min(ys) / h,
            "width": (max(xs) - min(xs)) / w,
            "height": (max(ys) - min(ys)) / h,
        }

    def to_dict(self) -> dict:
        return {
            "full_text": self.full_text,
            "lines": self.lines,
            "line_count": len(self.lines),
        }


class OCRRunner:
    """
    Singleton OCR engine.
    Initialize once at startup; call .run() per image.

    PaddleOCR natively supports ONNX inference via its use_onnx flag.
    For full NPU routing, export the detection + recognition models separately
    and pass them to build_session() from provider.py (advanced, Phase 2).
    For Phase 1, PaddleOCR's built-in ONNX mode runs efficiently on DirectML.
    """

    _instance: Optional["OCRRunner"] = None

    def __init__(self, lang: str = "en", use_gpu: bool = False):
        logger.info("Initializing OCR engine...")
        start = time.perf_counter()

        # use_angle_cls=True handles rotated text (common in scanned docs)
        # show_log=False suppresses verbose PaddleOCR output
        self._engine = PaddleOCR(
            use_angle_cls=True,
            lang=lang,
            use_gpu=use_gpu,
            show_log=False,
            # To use ONNX models explicitly (advanced):
            # det_model_dir="./models/det_onnx/",
            # rec_model_dir="./models/rec_onnx/",
            # use_onnx=True,
        )

        elapsed = time.perf_counter() - start
        logger.success(f"OCR engine ready in {elapsed:.2f}s")

    @classmethod
    def get_instance(cls, lang: str = "en") -> "OCRRunner":
        """Singleton access — only one engine loaded in memory."""
        if cls._instance is None:
            cls._instance = cls(lang=lang)
        return cls._instance

    def run(self, image: Image.Image) -> OCRResult:
        """
        Run OCR on a PIL Image.

        Args:
            image: PIL Image (RGB). Convert before passing if needed.

        Returns:
            OCRResult with full_text and per-line data including bboxes.
        """
        img_array = np.array(image.convert("RGB"))
        start = time.perf_counter()

        raw = self._engine.ocr(img_array, cls=True)

        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.debug(f"OCR inference: {elapsed_ms:.1f}ms")

        result = OCRResult(raw, image.size)
        logger.debug(
            f"Extracted {result.line_count} lines, "
            f"{len(result.full_text)} chars"
        )
        return result

    def run_from_path(self, image_path: str | Path) -> OCRResult:
        """Convenience wrapper — loads image from disk then runs OCR."""
        image = Image.open(str(image_path))
        return self.run(image)
