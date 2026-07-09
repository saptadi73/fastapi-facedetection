from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from services.embedding_service import embedding_service


@dataclass
class MatchResult:
    employee_map_id: Optional[int]
    similarity: float
    template_id: Optional[int] = None


@dataclass
class IndexEntry:
    employee_map_id: int
    embedding: list[float]
    template_id: Optional[int] = None


class FaissService:
    """
    In-memory nearest-neighbor placeholder.
    Replace with real FAISS index in production.
    """

    def __init__(self) -> None:
        self._index: list[IndexEntry] = []

    def add_embedding(
        self,
        employee_map_id: int,
        embedding: list[float],
        template_id: Optional[int] = None,
    ) -> None:
        self._index.append(
            IndexEntry(
                employee_map_id=employee_map_id,
                embedding=embedding,
                template_id=template_id,
            )
        )

    def clear(self) -> None:
        self._index.clear()

    def is_empty(self) -> bool:
        return len(self._index) == 0

    def remove_embedding(self, employee_map_id: int) -> None:
        self._index = [entry for entry in self._index if entry.employee_map_id != employee_map_id]

    def search(self, embedding: list[float], threshold: float = 0.75) -> MatchResult:
        best_id: Optional[int] = None
        best_template_id: Optional[int] = None
        best_score = -1.0

        for entry in self._index:
            score = embedding_service.cosine_similarity(embedding, entry.embedding)
            if score > best_score:
                best_score = score
                best_id = entry.employee_map_id
                best_template_id = entry.template_id

        if best_score < threshold:
            return MatchResult(employee_map_id=None, similarity=max(best_score, 0.0))

        return MatchResult(employee_map_id=best_id, similarity=best_score, template_id=best_template_id)


faiss_service = FaissService()
