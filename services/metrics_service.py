from __future__ import annotations

from collections import Counter
from threading import Lock
from time import perf_counter


class MetricsService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._requests = 0
        self._request_failures = 0
        self._total_latency_ms = 0.0
        self._status_codes: Counter[str] = Counter()
        self._paths: Counter[str] = Counter()

    def observe_request(self, path: str, status_code: int, started_at: float) -> None:
        latency_ms = (perf_counter() - started_at) * 1000
        with self._lock:
            self._requests += 1
            self._request_failures += int(status_code >= 400)
            self._total_latency_ms += latency_ms
            self._status_codes[str(status_code)] += 1
            self._paths[path] += 1

    def snapshot(self) -> dict:
        with self._lock:
            requests = self._requests
            return {
                "requests_total": requests,
                "request_failures_total": self._request_failures,
                "request_avg_latency_ms": round(self._total_latency_ms / requests, 2) if requests else 0.0,
                "status_codes": dict(self._status_codes),
                "paths": dict(self._paths),
            }


metrics_service = MetricsService()
