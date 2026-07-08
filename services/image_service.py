from __future__ import annotations

import base64
import io
from dataclasses import dataclass

from PIL import Image, ImageFilter, ImageStat


@dataclass
class ImageQuality:
    blur_score: float
    brightness_score: float
    width: int
    height: int


class ImageService:
    def decode_base64(self, image_base64: str) -> bytes:
        raw = image_base64.split(",", 1)[-1]
        return base64.b64decode(raw)

    def open_image(self, image_bytes: bytes) -> Image.Image:
        return Image.open(io.BytesIO(image_bytes)).convert("RGB")

    def evaluate_quality(self, image: Image.Image) -> ImageQuality:
        gray = image.convert("L")
        stat = ImageStat.Stat(gray)
        brightness = float(stat.mean[0])

        edges = gray.filter(ImageFilter.FIND_EDGES)
        edge_stat = ImageStat.Stat(edges)
        blur_score = float(edge_stat.var[0])

        return ImageQuality(
            blur_score=blur_score,
            brightness_score=brightness,
            width=image.width,
            height=image.height,
        )


image_service = ImageService()
