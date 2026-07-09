from __future__ import annotations

import ctypes
import importlib.util
import platform
from pathlib import Path
from typing import Optional

from config.settings import settings


class SystemHealthService:
    def inference_health(self) -> dict:
        cpu_features = self._cpu_features()
        onnxruntime_installed = importlib.util.find_spec("onnxruntime") is not None
        available_providers: list[str] = []
        if onnxruntime_installed:
            import onnxruntime as ort

            available_providers = list(ort.get_available_providers())

        configured_providers = [
            provider.strip()
            for provider in settings.face_onnx_execution_providers.split(",")
            if provider.strip()
        ]
        model_path = self._resolve_model_path(settings.face_onnx_model_path)
        model_exists = bool(model_path and model_path.exists())

        return {
            "embedding_provider": settings.face_embedding_provider,
            "recognition_threshold": settings.face_recognition_threshold,
            "cpu": {
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "avx_available": cpu_features.get("avx"),
                "avx2_available": cpu_features.get("avx2"),
                "avx512f_available": cpu_features.get("avx512f"),
                "avx_passed": cpu_features.get("avx") is True,
                "avx2_passed": cpu_features.get("avx2") is True,
                "source": cpu_features.get("source"),
            },
            "onnxruntime": {
                "installed": onnxruntime_installed,
                "available_providers": available_providers,
                "configured_providers": configured_providers,
                "provider_available": all(provider in available_providers for provider in configured_providers)
                if configured_providers
                else False,
            },
            "model": {
                "path": str(model_path) if model_path else "",
                "exists": model_exists,
                "input_size": settings.face_onnx_input_size,
            },
        }

    def _resolve_model_path(self, configured_path: str) -> Optional[Path]:
        if not configured_path:
            return None
        model_path = Path(configured_path)
        if not model_path.is_absolute():
            model_path = Path(settings.base_dir) / model_path
        return model_path

    def _cpu_features(self) -> dict[str, Optional[bool] | str]:
        if platform.system().lower() == "windows":
            return self._windows_cpu_features()
        return self._linux_cpu_features()

    def _windows_cpu_features(self) -> dict[str, Optional[bool] | str]:
        try:
            kernel32 = ctypes.windll.kernel32
            return {
                "avx": bool(kernel32.IsProcessorFeaturePresent(39)),
                "avx2": bool(kernel32.IsProcessorFeaturePresent(40)),
                "avx512f": bool(kernel32.IsProcessorFeaturePresent(41)),
                "source": "IsProcessorFeaturePresent",
            }
        except Exception:
            return {"avx": None, "avx2": None, "avx512f": None, "source": "unavailable"}

    def _linux_cpu_features(self) -> dict[str, Optional[bool] | str]:
        cpuinfo = Path("/proc/cpuinfo")
        if not cpuinfo.exists():
            return {"avx": None, "avx2": None, "avx512f": None, "source": "unavailable"}

        flags_text = cpuinfo.read_text(encoding="utf-8", errors="ignore").lower()
        flags = set(flags_text.replace("\n", " ").split())
        return {
            "avx": "avx" in flags,
            "avx2": "avx2" in flags,
            "avx512f": "avx512f" in flags,
            "source": "/proc/cpuinfo",
        }


system_health_service = SystemHealthService()
