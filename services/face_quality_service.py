from __future__ import annotations

from dataclasses import dataclass

from config.settings import settings
from services.image_service import ImageQuality
from services.mediapipe_service import FaceAnalysis


@dataclass
class FaceQualityDecision:
    accepted: bool
    reason_codes: list[str]


class FaceQualityService:
    def evaluate(self, face: FaceAnalysis, quality: ImageQuality) -> FaceQualityDecision:
        reason_codes: list[str] = []

        if face.face_count != 1:
            reason_codes.append("INVALID_FACE_COUNT")
        if face.confidence < settings.face_min_detection_confidence:
            reason_codes.append("LOW_DETECTION_CONFIDENCE")
        if quality.blur_score < settings.face_min_blur_score:
            reason_codes.append("BLUR_TOO_LOW")
        if quality.brightness_score < settings.face_min_brightness_score:
            reason_codes.append("IMAGE_TOO_DARK")
        if quality.brightness_score > settings.face_max_brightness_score:
            reason_codes.append("IMAGE_TOO_BRIGHT")

        return FaceQualityDecision(
            accepted=len(reason_codes) == 0,
            reason_codes=reason_codes,
        )


face_quality_service = FaceQualityService()
