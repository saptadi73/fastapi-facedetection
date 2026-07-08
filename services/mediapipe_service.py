from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FaceAnalysis:
    face_count: int
    confidence: float
    yaw: float
    pitch: float
    roll: float


class MediaPipeService:
    """
    Placeholder detector.
    Real implementation can be swapped in with MediaPipe FaceDetection + FaceMesh.
    """

    def detect(self, image_width: int, image_height: int) -> FaceAnalysis:
        if image_width < 120 or image_height < 120:
            return FaceAnalysis(face_count=0, confidence=0.1, yaw=0.0, pitch=0.0, roll=0.0)

        return FaceAnalysis(face_count=1, confidence=0.95, yaw=0.0, pitch=0.0, roll=0.0)


mediapipe_service = MediaPipeService()
