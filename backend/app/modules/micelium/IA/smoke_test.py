from __future__ import annotations

from app.modules.micelium.IA.prediction_service import MiceliumAIService
from app.modules.micelium.IA.schemas import MiceliumAIPredictionRequest
from app.modules.micelium.IA.tests_payloads import (
    CAPB_PAYLOAD,
    CTAB_PAYLOAD,
    SDS_PAYLOAD,
    TWEEN_80_PAYLOAD,
)


def main() -> None:
    service = MiceliumAIService()

    for payload in [SDS_PAYLOAD, CTAB_PAYLOAD, TWEEN_80_PAYLOAD, CAPB_PAYLOAD]:
        request = MiceliumAIPredictionRequest.model_validate(payload)
        response = service.predict(request)
        print(
            payload["name"],
            response.molecule.surfactant_class,
            response.prediction.ai_route,
            response.prediction.predicted_cmc_mmol_l,
            response.prediction.predicted_effective_hlb,
        )


if __name__ == "__main__":
    main()


