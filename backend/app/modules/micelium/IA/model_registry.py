from __future__ import annotations

import math

from pathlib import Path
from typing import Any

from app.modules.micelium.IA.schemas import AIRoute


try:
    import joblib
except Exception:  # pragma: no cover
    joblib = None


class ModelRegistry:
    """
    Carrega modelos treinados salvos em arquivo.

    O caminho padrão é relativo a este arquivo, não ao diretório onde o uvicorn foi iniciado.
    """

    def __init__(self, model_dir: str | Path | None = None) -> None:
        self.model_dir = Path(model_dir) if model_dir else Path(__file__).resolve().parent / "trained_models"
        self._cache: dict[str, Any] = {}

    def model_path(self, route: AIRoute, target: str) -> Path:
        return self.model_dir / str(route) / f"{target}.joblib"

    def load(self, route: AIRoute, target: str) -> Any | None:
        key = f"{route}:{target}"

        if key in self._cache:
            return self._cache[key]

        if joblib is None:
            self._cache[key] = None
            return None

        path = self.model_path(route, target)

        if not path.exists():
            self._cache[key] = None
            return None

        try:
            model = joblib.load(path)
        except Exception:
            model = None
        self._cache[key] = model
        return model

    def predict_one(
        self,
        *,
        route: AIRoute,
        target: str,
        features: list[float],
    ) -> float | None:
        model = self.load(route, target)

        if model is None:
            return None

        try:
            result = model.predict([features])
        except Exception:
            return None

        if result is None or len(result) == 0:
            return None

        try:
            value = float(result[0])
            if not math.isfinite(value) or (target == "cmc_mmol_l" and value <= 0):
                return None
            return value
        except (TypeError, ValueError):
            return None
