from __future__ import annotations

from app.modules.micelium.IA.headgroup_classifier import classify_cationic_headgroup
from app.modules.micelium.IA.prediction_service import MiceliumAIService
from app.modules.micelium.IA.schemas import MiceliumAIPredictionRequest


def test_octylammonium_chloride_classifier() -> None:
    smiles = "CCCCCCCC[NH3+].[Cl-]"
    result = classify_cationic_headgroup("CCCCCCCC[NH3+]")

    assert result.head_group == "PRIMARY_ALKYLAMMONIUM_SURFACTANT"
    assert result.ammonium_subtype == "primary_ammonium"
    assert result.head_area_a2 is not None
    assert result.head_area_a2 < 45.0


def test_octylammonium_chloride_ai_route() -> None:
    service = MiceliumAIService()
    response = service.predict(
        MiceliumAIPredictionRequest(
            name="octylammonium chloride",
            smiles="CCCCCCCC[NH3+].[Cl-]",
            environment={
                "surfactant_concentration_mmol_l": 200.0,
                "volume_ml": 100.0,
            },
        )
    )

    assert response.molecule.surfactant_class == "cationic"
    assert response.molecule.descriptors.head_group == "PRIMARY_ALKYLAMMONIUM_SURFACTANT"
    assert response.molecule.descriptors.ammonium_subtype == "primary_ammonium"
    assert response.prediction.predicted_effective_hlb is not None
    assert response.prediction.predicted_cmc_mmol_l is not None


if __name__ == "__main__":
    test_octylammonium_chloride_classifier()
    test_octylammonium_chloride_ai_route()
    print("OK: octylammonium chloride classificado como amônio primário.")


