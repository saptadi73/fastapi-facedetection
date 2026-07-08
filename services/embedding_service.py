from __future__ import annotations

import hashlib
import math


class EmbeddingService:
    def generate_embedding(self, image_bytes: bytes, dim: int = 128) -> list[float]:
        digest = hashlib.sha512(image_bytes).digest()
        values: list[float] = []

        while len(values) < dim:
            digest = hashlib.sha512(digest).digest()
            values.extend((byte / 255.0) * 2 - 1 for byte in digest)

        vector = values[:dim]
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / norm for x in vector]

    def cosine_similarity(self, vector_a: list[float], vector_b: list[float]) -> float:
        if len(vector_a) != len(vector_b):
            return 0.0

        dot = sum(a * b for a, b in zip(vector_a, vector_b))
        norm_a = math.sqrt(sum(a * a for a in vector_a)) or 1.0
        norm_b = math.sqrt(sum(b * b for b in vector_b)) or 1.0
        return dot / (norm_a * norm_b)


embedding_service = EmbeddingService()
