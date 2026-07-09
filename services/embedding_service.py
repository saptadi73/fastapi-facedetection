from __future__ import annotations

import io
import math
from pathlib import Path
from typing import Any, Optional

from config.settings import settings
from PIL import Image, ImageChops, ImageOps, ImageStat


class EmbeddingService:
    def __init__(self) -> None:
        self._onnx_session: Any = None
        self._onnx_input_name: Optional[str] = None
        self._onnx_output_name: Optional[str] = None
        self._onnx_error: Optional[str] = None

    def generate_embedding(self, image_bytes: bytes, dim: int = 0) -> list[float]:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        vector = self._generate_vector(image)
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / norm for x in vector]

    def provider_name(self) -> str:
        provider = settings.face_embedding_provider.strip().lower()
        if provider == "onnx":
            return "onnx"
        if provider == "auto" and self._can_use_onnx():
            return "onnx"
        return "visual"

    def _generate_vector(self, image: Image.Image) -> list[float]:
        provider = settings.face_embedding_provider.strip().lower()
        if provider == "onnx":
            return self._onnx_feature_vector(image)
        if provider == "auto" and self._can_use_onnx():
            return self._onnx_feature_vector(image)
        return self._image_feature_vector(image)

    def _can_use_onnx(self) -> bool:
        if not settings.face_onnx_model_path:
            return False
        if self._onnx_session is not None:
            return True
        try:
            self._load_onnx_session()
            return True
        except Exception as exc:
            self._onnx_error = str(exc)
            return False

    def _load_onnx_session(self) -> None:
        model_path = Path(settings.face_onnx_model_path)
        if not model_path.is_absolute():
            model_path = Path(settings.base_dir) / model_path
        if not model_path.exists():
            raise FileNotFoundError(f"ONNX model not found: {model_path}")

        import onnxruntime as ort

        providers = [
            provider.strip()
            for provider in settings.face_onnx_execution_providers.split(",")
            if provider.strip()
        ] or ["CPUExecutionProvider"]
        self._onnx_session = ort.InferenceSession(str(model_path), providers=providers)
        session_inputs = self._onnx_session.get_inputs()
        session_outputs = self._onnx_session.get_outputs()
        self._onnx_input_name = settings.face_onnx_input_name or session_inputs[0].name
        self._onnx_output_name = settings.face_onnx_output_name or session_outputs[0].name

    def _onnx_feature_vector(self, image: Image.Image) -> list[float]:
        if not self._can_use_onnx():
            raise RuntimeError(self._onnx_error or "ONNX embedding provider is unavailable")

        import numpy as np

        input_size = settings.face_onnx_input_size
        fitted = ImageOps.fit(image, (input_size, input_size), method=Image.Resampling.BILINEAR)
        array = np.asarray(fitted, dtype=np.float32)
        array = (array - 127.5) / 128.0
        array = np.transpose(array, (2, 0, 1))[None, :, :, :]

        outputs = self._onnx_session.run([self._onnx_output_name], {self._onnx_input_name: array})
        embedding = np.asarray(outputs[0], dtype=np.float32).reshape(-1)
        return embedding.tolist()

    def _image_feature_vector(self, image: Image.Image) -> list[float]:
        fitted = ImageOps.fit(image, (32, 32), method=Image.Resampling.BILINEAR)
        gray = fitted.convert("L")
        equalized = ImageOps.equalize(gray)
        stat = ImageStat.Stat(equalized)
        mean = float(stat.mean[0])
        stddev = float(stat.stddev[0]) or 1.0

        pixels = list(equalized.getdata())
        intensity_features = [(pixel - mean) / (stddev * 4.0) for pixel in pixels]

        shifted_x = ImageChops.offset(equalized, -1, 0)
        shifted_y = ImageChops.offset(equalized, 0, -1)
        gradient_x = ImageChops.difference(equalized, shifted_x)
        gradient_y = ImageChops.difference(equalized, shifted_y)
        gradient_features = [
            (gx + gy) / 510.0
            for gx, gy in zip(gradient_x.getdata(), gradient_y.getdata())
        ]

        histogram_features: list[float] = []
        for channel in fitted.split():
            histogram = channel.histogram()
            total = sum(histogram) or 1
            for bucket_start in range(0, 256, 16):
                histogram_features.append(sum(histogram[bucket_start : bucket_start + 16]) / total)

        return intensity_features + gradient_features + histogram_features

    def cosine_similarity(self, vector_a: list[float], vector_b: list[float]) -> float:
        if len(vector_a) != len(vector_b):
            return 0.0

        dot = sum(a * b for a, b in zip(vector_a, vector_b))
        norm_a = math.sqrt(sum(a * a for a in vector_a)) or 1.0
        norm_b = math.sqrt(sum(b * b for b in vector_b)) or 1.0
        return dot / (norm_a * norm_b)


embedding_service = EmbeddingService()
