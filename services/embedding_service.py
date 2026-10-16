from __future__ import annotations

import io
import math
from pathlib import Path
from threading import Lock
from typing import Any, Optional

from config.settings import settings
from PIL import Image, ImageChops, ImageOps, ImageStat


class EmbeddingService:
    def __init__(self) -> None:
        self._onnx_session: Any = None
        self._onnx_input_name: Optional[str] = None
        self._onnx_output_name: Optional[str] = None
        self._onnx_error: Optional[str] = None
        self._face_detector_yn: Any = None
        self._face_alignment_error: Optional[str] = None
        self._face_detector_lock = Lock()

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

    def health(self) -> dict:
        configured = settings.face_embedding_provider.strip().lower()
        onnx_ready = self._can_use_onnx() if configured in {"onnx", "auto"} else False
        ready = onnx_ready if configured == "onnx" else True
        alignment_model = self._resolve_alignment_model()
        return {
            "configured_provider": configured,
            "active_provider": self.provider_name(),
            "ready": ready,
            "onnx_ready": onnx_ready,
            "onnx_error": self._onnx_error,
            "face_alignment": {
                "configured": True,
                "model_exists": alignment_model.is_file(),
                "active": self._load_face_detector_yn() is not None,
                "error": self._face_alignment_error,
            },
        }

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

    def _resolve_alignment_model(self) -> Path:
        model_path = Path(settings.face_alignment_model_path)
        return model_path if model_path.is_absolute() else Path(settings.base_dir) / model_path

    def _load_face_detector_yn(self):
        if self._face_detector_yn is not None:
            return self._face_detector_yn
        try:
            import cv2
            if not hasattr(cv2, "FaceDetectorYN_create"):
                raise RuntimeError("OpenCV FaceDetectorYN is unavailable")
            model_path = self._resolve_alignment_model()
            if not model_path.is_file():
                raise FileNotFoundError(f"YuNet alignment model not found: {model_path}")
            self._face_detector_yn = cv2.FaceDetectorYN_create(
                str(model_path), "", (320, 320), 0.6, 0.3, 5000
            )
            return self._face_detector_yn
        except Exception as exc:
            self._face_alignment_error = str(exc)
            return None

    def _crop_face(self, image: Image.Image) -> Image.Image:
        """Align a face to the canonical 112x112 ArcFace landmark template."""
        try:
            import cv2
            import numpy as np

            rgb = np.asarray(image.convert("RGB"))
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            detector = self._load_face_detector_yn()
            if detector is not None:
                with self._face_detector_lock:
                    detector.setInputSize((bgr.shape[1], bgr.shape[0]))
                    _, faces = detector.detect(bgr)
                if faces is not None and len(faces):
                    face = max(faces, key=lambda row: float(row[2] * row[3]))
                    landmarks = np.asarray(face[4:14], dtype=np.float32).reshape(5, 2)
                    reference = np.array([
                        [38.2946, 51.6963], [73.5318, 51.5014],
                        [56.0252, 71.7366], [41.5493, 92.3655],
                        [70.7299, 92.2041],
                    ], dtype=np.float32)
                    target_size = int(settings.face_onnx_input_size)
                    reference *= target_size / 112.0
                    transform, _ = cv2.estimateAffinePartial2D(
                        landmarks, reference, method=cv2.LMEDS
                    )
                    if transform is not None and np.isfinite(transform).all():
                        aligned_bgr = cv2.warpAffine(
                            bgr, transform, (target_size, target_size),
                            flags=cv2.INTER_LINEAR,
                            borderMode=cv2.BORDER_CONSTANT,
                            borderValue=(0, 0, 0),
                        )
                        aligned_rgb = cv2.cvtColor(aligned_bgr, cv2.COLOR_BGR2RGB)
                        self._face_alignment_error = None
                        return Image.fromarray(aligned_rgb)

            # Safe fallback if YuNet cannot locate landmarks: use a tight Haar
            # crop rather than embedding the full camera frame/background.
            cascade_path = settings.face_detector_cascade_path
            if not cascade_path:
                cascade_path = str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml")
            cascade = cv2.CascadeClassifier(cascade_path)
            gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
            faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
            if len(faces):
                x, y, width, height = max(faces, key=lambda box: int(box[2]) * int(box[3]))
                margin = int(max(width, height) * 0.10)
                crop = rgb[max(0, y-margin):min(rgb.shape[0], y+height+margin), max(0, x-margin):min(rgb.shape[1], x+width+margin)]
                return Image.fromarray(crop)
            return image
        except Exception as exc:
            self._face_alignment_error = str(exc)
            return image

    def _onnx_feature_vector(self, image: Image.Image) -> list[float]:
        if not self._can_use_onnx():
            raise RuntimeError(self._onnx_error or "ONNX embedding provider is unavailable")

        import numpy as np

        input_size = settings.face_onnx_input_size
        fitted = ImageOps.fit(self._crop_face(image), (input_size, input_size), method=Image.Resampling.BILINEAR)
        array = np.asarray(fitted, dtype=np.float32)
        array = (array - 127.5) / 128.0
        array = np.transpose(array, (2, 0, 1))[None, :, :, :]

        outputs = self._onnx_session.run([self._onnx_output_name], {self._onnx_input_name: array})
        embedding = np.asarray(outputs[0], dtype=np.float32).reshape(-1)
        return embedding.tolist()

    def _image_feature_vector(self, image: Image.Image) -> list[float]:
        fitted = ImageOps.fit(self._crop_face(image), (32, 32), method=Image.Resampling.BILINEAR)
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
