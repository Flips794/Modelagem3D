import copy
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.analysis_packages.repository import AnalysisPackageRepository
from app.modules.analysis_packages.schemas import AnalysisPackageCreate
from app.modules.chemistry.structural_hash_service import StructuralHashService


class AnalysisPackageService:
    def __init__(self, db: Session):
        self.repository = AnalysisPackageRepository(db)

    def create_package(self, payload: AnalysisPackageCreate):
        immutable_payload = copy.deepcopy(payload.model_dump())

        hash_payload = {
            "molecule_snapshot": immutable_payload["molecule_snapshot"],
            "chemical_analysis_snapshot": immutable_payload["chemical_analysis_snapshot"],
            "descriptors_2d_snapshot": immutable_payload["descriptors_2d_snapshot"],
            "package_version": immutable_payload["package_version"],
            "engine_version": immutable_payload["engine_version"],
        }

        structural_hash = StructuralHashService.create_hash(hash_payload)

        return self.repository.create(payload, structural_hash)

    def get_package(self, package_id: UUID):
        analysis_package = self.repository.get_by_id(package_id)

        if analysis_package is None:
            raise NotFoundError("Pacote de análise não encontrado.")

        return analysis_package

