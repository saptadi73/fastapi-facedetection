from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import math

from PIL import Image

from config.settings import settings


@dataclass
class FaceAnalysis:
    face_count: int
    confidence: float
    yaw: float
    pitch: float
    roll: float


class MediaPipeService:
    """
    Face detector adapter.

    ``opencv`` uses a Haar cascade and is intended as a CPU baseline. The
    legacy placeholder remains available for synthetic/local tests until a
    real pilot dataset is configured.
    """

    def __init__(self) -> None:
        self._cascade = None
        self._mediapipe_detector = None
        self._mediapipe_mesh = None
        provider = settings.face_detector_provider.lower()
        if provider == "opencv":
            self._cascade = self._load_cascade()
        elif provider == "mediapipe":
            self._mediapipe_detector, self._mediapipe_mesh = self._load_mediapipe()

    def _load_cascade(self):
        try:
            import cv2
        except Exception:
            return None
        cascade_path = settings.face_detector_cascade_path
        if not cascade_path:
            cascade_path = str(Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml")
        cascade = cv2.CascadeClassifier(cascade_path)
        return cascade if not cascade.empty() else None

    def _load_mediapipe(self):
        try:
            import mediapipe as mp
        except Exception:
            return None, None
        try:
            detector = mp.solutions.face_detection.FaceDetection(
                model_selection=0,
                min_detection_confidence=settings.face_min_detection_confidence,
            )
            mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=True,
                max_num_faces=3,
                refine_landmarks=True,
                min_detection_confidence=settings.face_min_detection_confidence,
                min_tracking_confidence=settings.face_min_detection_confidence,
            )
            return detector, mesh
        except Exception:
            return None, None

    def detect(self, image: Image.Image | int, image_height: Optional[int] = None) -> FaceAnalysis:
        provider = settings.face_detector_provider.lower()
        if provider == "mediapipe" and isinstance(image, Image.Image):
            return self._detect_mediapipe(image)
        if provider == "opencv" and isinstance(image, Image.Image):
            return self._detect_opencv(image)

        image_width = image if isinstance(image, int) else image.width
        height = image_height if image_height is not None else image.height
        if image_width < 120 or height < 120:
            return FaceAnalysis(face_count=0, confidence=0.1, yaw=0.0, pitch=0.0, roll=0.0)

        return FaceAnalysis(face_count=1, confidence=0.95, yaw=0.0, pitch=0.0, roll=0.0)

    def _detect_mediapipe(self, image: Image.Image) -> FaceAnalysis:
        if self._mediapipe_detector is None:
            return FaceAnalysis(face_count=0, confidence=0.0, yaw=0.0, pitch=0.0, roll=0.0)
        import numpy as np

        pixels = np.asarray(image.convert("RGB"))
        result = self._mediapipe_detector.process(pixels)
        detections = result.detections or []
        confidence = max(
            (float(detection.score[0]) for detection in detections if detection.score),
            default=0.0,
        )
        yaw, pitch, roll = 0.0, 0.0, 0.0
        if detections and self._mediapipe_mesh is not None:
            mesh_result = self._mediapipe_mesh.process(pixels)
            if mesh_result.multi_face_landmarks:
                yaw, pitch, roll = self._estimate_pose(
                    mesh_result.multi_face_landmarks[0].landmark,
                    image.width,
                    image.height,
                )
        return FaceAnalysis(
            face_count=len(detections),
            confidence=confidence,
            yaw=yaw,
            pitch=pitch,
            roll=roll,
        )

    @staticmethod
    def _estimate_pose(landmarks, width: int, height: int) -> tuple[float, float, float]:
        """Estimate Euler angles from six Face Mesh landmarks."""
        import cv2
        import numpy as np

        image_points = np.array([
            (landmarks[1].x * width, landmarks[1].y * height),
            (landmarks[152].x * width, landmarks[152].y * height),
            (landmarks[33].x * width, landmarks[33].y * height),
            (landmarks[263].x * width, landmarks[263].y * height),
            (landmarks[61].x * width, landmarks[61].y * height),
            (landmarks[291].x * width, landmarks[291].y * height),
        ], dtype=np.float64)
        model_points = np.array([
            (0.0, 0.0, 0.0),
            (0.0, -63.6, -12.5),
            (-43.3, 32.7, -26.0),
            (43.3, 32.7, -26.0),
            (-28.9, -28.9, -24.1),
            (28.9, -28.9, -24.1),
        ], dtype=np.float64)
        focal_length = width
        camera_matrix = np.array([
            [focal_length, 0, width / 2],
            [0, focal_length, height / 2],
            [0, 0, 1],
        ], dtype=np.float64)
        success, rotation_vector, _ = cv2.solvePnP(
            model_points,
            image_points,
            camera_matrix,
            np.zeros((4, 1)),
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if not success:
            return 0.0, 0.0, 0.0
        rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
        sy = math.sqrt(rotation_matrix[0, 0] ** 2 + rotation_matrix[1, 0] ** 2)
        pitch = math.degrees(math.atan2(rotation_matrix[2, 1], rotation_matrix[2, 2]))
        yaw = math.degrees(math.atan2(-rotation_matrix[2, 0], sy))
        roll = math.degrees(math.atan2(rotation_matrix[1, 0], rotation_matrix[0, 0]))
        return yaw, pitch, roll

    def _detect_opencv(self, image: Image.Image) -> FaceAnalysis:
        if self._cascade is None:
            return FaceAnalysis(face_count=0, confidence=0.0, yaw=0.0, pitch=0.0, roll=0.0)
        import cv2
        import numpy as np

        pixels = np.asarray(image.convert("RGB"))
        gray = cv2.cvtColor(pixels, cv2.COLOR_RGB2GRAY)
        faces = self._cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60),
        )
        return FaceAnalysis(
            face_count=len(faces),
            confidence=0.85 if len(faces) else 0.0,
            yaw=0.0,
            pitch=0.0,
            roll=0.0,
        )


mediapipe_service = MediaPipeService()
