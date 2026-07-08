from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from services.embedding_service import embedding_service


@dataclass
class MatchResult:
    employee_map_id: Optional[int]
    similarity: float


class FaissService:
    """
    In-memory nearest-neighbor placeholder.
    Replace with real FAISS index in production.
    """

    def __init__(self) -> None:
        self._index: dict[int, list[float]] = {}

    def add_embedding(self, employee_map_id: int, embedding: list[float]) -> None:
        self._index[employee_map_id] = embedding

    def remove_embedding(self, employee_map_id: int) -> None:
        self._index.pop(employee_map_id, None)

    def search(self, embedding: list[float], threshold: float = 0.75) -> MatchResult:
        best_id: Optional[int] = None
        best_score = -1.0

        for employee_map_id, stored_vector in self._index.items():
            score = embedding_service.cosine_similarity(embedding, stored_vector)
            if score > best_score:
                best_score = score
                best_id = employee_map_id

        if best_score < threshold:
            return MatchResult(employee_map_id=None, similarity=max(best_score, 0.0))

        return MatchResult(employee_map_id=best_id, similarity=best_score)


faiss_service = FaissService()
